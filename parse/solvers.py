# encoding: utf-8
"""
自动解题
default interpreter: python3
Created on 2018-04-25
@author: wangguojie
"""
import os
import sys
import re as rex
sys.path.append(os.path.join(os.path.expanduser("~"), "git/latex2sympy"))
sys.path.append('')
sys.path.append(os.path.abspath(os.path.join('', os.pardir)))
print(os.path.abspath(os.path.join('', os.pardir)))


from core.util import *
import pandas as pd
import networkx as nx
from pymongo import MongoClient
from process_latex import process_sympy
from sympy.parsing.sympy_parser import parse_expr
from sts_algebra import Alegbra
from element_recognition import ElementRecognition
from parse import expr2graph
from sympy import *

# import logging


# mi数据库
mi = MongoClient(host="10.8.8.71", connect=False)['mi']


# 新建日志目录
# if not os.path.isdir("logs"):
#     os.mkdir("logs")
# logging.basicConfig(level=logging.DEBUG,
#                     format='%(lineno)d %(asctime)s %(name)-12s %(levelname)-8s %(message)s',
#                     datefmt='%m-%d %H:%M',
#                     filename="logs/error.log",
#                     filemode='w')
# logger = logging.getLogger('huluwa')


# 日志记录
log_info = []


# 解题模板相关信息
# name, input_elements, steps
theme_info = dict()
debug = True


def get_theme_info():
    global theme_info
    # 基础模板与拆分子模板的名称映射,由Switch分支引起
    base_theme_2_sub_themes = dict()
    for dat in mi['solutions_themes'].find({'type': 'core'}):
        base_name = dat['name']
        input_elements = dat['input_elements'].split(', ')
        steps_this_tmp = dat['steps'].split(', ')
        steps_those = []
        i = 0
        while i < len(steps_this_tmp):
            step = steps_this_tmp[i]
            if step != 'SWITCH':
                if len(steps_those) == 0:
                    steps_those.append([step])
                else:
                    for steps in steps_those:
                        steps.append(step)
                i += 1
            else:
                # 处理 'SWITCH' 与 'END SWITCH' 之间的步骤
                j = i + 1
                case_steps = []
                while j < len(steps_this_tmp):
                    if steps_this_tmp[j] == 'END SWITCH':
                        break
                    if steps_this_tmp[j] == 'CASE':
                        k = j + 1
                        case_steps_this = []
                        while k < len(steps_this_tmp):
                            if steps_this_tmp[k] == 'CASE' or steps_this_tmp[k] == 'END SWITCH':
                                if len(case_steps_this) > 0:
                                    case_steps.append(case_steps_this)
                                break
                            else:
                                s = steps_this_tmp[k]
                                case_steps_this.append(s)
                                k += 1
                        j = k - 1
                    j += 1
                i = j + 1
                # case_steps
                if len(steps_those) == 0:
                    steps_those = case_steps
                else:
                    steps_those_tmp = []
                    for s1 in steps_those:
                        for s2 in case_steps:
                            steps_those_tmp.append(s1 + s2)
                    steps_those = steps_those_tmp
        for i in range(len(steps_those)):
            theme_name = base_name
            if len(steps_those) > 1:
                theme_name = base_name + '-' + str(i + 1)
            theme_info[theme_name] = {'input_elements': input_elements,
                                      'steps': steps_those[i]}
            if base_name in base_theme_2_sub_themes:
                base_theme_2_sub_themes[base_name].update([theme_name])
            else:
                base_theme_2_sub_themes[base_name] = set([theme_name])

    # 注意判断模板的加载顺序,保证引用其他模板时,必须加载完成,模板工厂不支持任何形式递归(直接的或间接的)
    # 建立一个有向图,从根节点遍历
    theme_dat_list = dict()
    dat_list = mi['solutions_themes'].find({'type': 'block'})
    g = nx.nx.DiGraph()
    for dat in dat_list:
        theme_dat_list[dat['name']] = dat
        # 建立模板之间的有向边
        for step in dat['steps'].split(', '):
            if step.startswith('模板:'):
                g.add_edge(step[3:], dat['name'])
    theme_list = list(list(nx.topological_sort(g)))
    print('theme_list:', theme_list)
    print('base_theme_2_sub_themes:', base_theme_2_sub_themes)
    for theme in theme_list:
        # 排除基础模板
        if theme not in theme_dat_list:
            continue
        dat = theme_dat_list[theme]
        # 分支模板命名规则是 '基础模板名字'+'-'+'id编号 1-n'
        base_name = dat['name']
        input_elements = dat['input_elements'].split(', ')
        steps_those = []
        steps_this_tmp = dat['steps'].split(', ')
        # print('steps_this_tmp:', steps_this_tmp)
        i = 0
        while i < len(steps_this_tmp):
            step = steps_this_tmp[i]
            if step != 'SWITCH':
                if step.startswith('模板:'):
                    if len(steps_those) == 0:
                        # steps_those.append(theme_info[step[3:]]['steps'])
                        for theme_this in base_theme_2_sub_themes[step[3:]]:
                            steps_those.append(theme_info[theme_this]['steps'])
                    else:
                        steps_those_tmp = []
                        for theme_this in base_theme_2_sub_themes[step[3:]]:
                            for steps in steps_those:
                                steps_those_tmp.append(steps + theme_info[theme_this]['steps'])
                        steps_those = steps_those_tmp
                else:
                    if len(steps_those) == 0:
                        steps_those.append([step])
                    else:
                        for steps in steps_those:
                            steps.append(step)
                i += 1
            else:
                # 处理 'SWITCH' 与 'END SWITCH' 之间的步骤
                j = i + 1
                case_steps = []  # [[s1,s2,...],[s1,s2,...],...]
                while j < len(steps_this_tmp):
                    if steps_this_tmp[j] == 'END SWITCH':
                        break
                    if steps_this_tmp[j] == 'CASE':
                        k = j + 1
                        case_steps_this = []  # [[s1,s2,...],[s1,s2,...],...]
                        while k < len(steps_this_tmp):
                            if steps_this_tmp[k] == 'CASE' or steps_this_tmp[k] == 'END SWITCH':
                                if len(case_steps_this) > 0:
                                    # case_steps.append(case_steps_this)
                                    case_steps.extend(case_steps_this)
                                break
                            else:
                                s = steps_this_tmp[k]
                                if s.startswith('模板:'):
                                    if len(case_steps_this) > 0:
                                        case_steps_this_tmp = []
                                        for theme_this in base_theme_2_sub_themes[s[3:]]:
                                            for steps in case_steps_this:
                                                case_steps_this_tmp.append(steps + theme_info[theme_this]['steps'])
                                        case_steps_this = case_steps_this_tmp
                                    else:
                                        for theme_this in base_theme_2_sub_themes[s[3:]]:
                                            case_steps_this.append(theme_info[theme_this]['steps'])
                                else:
                                    if len(case_steps_this) > 0:
                                        for steps in case_steps_this:
                                            steps.append(s)
                                    else:
                                        case_steps_this.append([s])
                                k += 1
                        j = k - 1
                    j += 1
                i = j + 1
                # case_steps
                if len(steps_those) == 0:
                    steps_those = case_steps
                else:
                    steps_those_tmp = []
                    for s1 in steps_those:
                        for s2 in case_steps:
                            steps_those_tmp.append(s1 + s2)
                    steps_those = steps_those_tmp
        # print('steps_those:', steps_those)
        for i in range(len(steps_those)):
            theme_name = base_name
            if len(steps_those) > 1:
                theme_name = base_name + '-' + str(i + 1)
            theme_info[theme_name] = {'input_elements': input_elements,
                                      'steps': steps_those[i]}
            if base_name in base_theme_2_sub_themes:
                base_theme_2_sub_themes[base_name].update([theme_name])
            else:
                base_theme_2_sub_themes[base_name] = set([theme_name])
    # print('base_theme_2_sub_themes:', base_theme_2_sub_themes)
    print('theme_info:', theme_info)


step_info = dict()


def get_step_info():
    global step_info
    # 解题步骤相关信息
    # name, input_elements, output_elements, check_func, core_func, type
    for dat in mi['solutions_steps'].find({}):
        try:
            step_info_this = dict()
            step_info_this['input_elements'] = dat['input_elements'].split(', ')
            step_info_this['output_elements'] = dat['output_elements'].split(', ')
            exec(dat['func'])
            func_name = rex.findall('def(.*?)\\(', dat['func'])[0].strip(' ')
            step_info_this['core_func'] = eval(func_name)
            dat['check'] = dat['check'].replace(' check(', ''.join([' ', func_name, '_check(']))
            exec(dat['check'])
            step_info_this['check_func'] = eval(rex.findall('def(.*?)\\(', dat['check'])[0].strip(' '))
            step_info_this['type'] = dat['type']
            name = dat['name']
            step_info[name] = step_info_this
        except:
            print(sys.exc_info(), dat)
    print('step info:', step_info)


element_relations = dict()


def get_element_relations():
    global element_relations
    for dat in list(mi['elements'].find({'type': 'edge'})):
        if dat['element'] in element_relations:
            element_relations[dat['element']].update([dat['par_element']])
        else:
            element_relations[dat['element']] = set([dat['par_element']])


def atom_theme_solvers(expr, theme):
    """
        模板求解
        NOTE:
            暂不支持循环嵌套
        :return
            result_list:
                [{'desc':desc1, 'expr': expr1},
                 {'desc':desc2, 'expr': expr2},
                 ...]
            end_flag:
                求解结束标志 True/False
    """
    global step_info, theme_info, log_info
    rst = []

    # 是否完成该模板标志
    end_flag = False

    # 注意处理LOOP问题, LOOP是一个整体
    # 先提出所有的LOOP和END LOOP,然后进行单独循环
    # [step1, step2, ...], [LOOP], [step, step, ...]
    steps_list = []
    steps = []
    # print(theme_info[theme]['steps'])

    # 先提取出initial_list
    initial_list = []
    pos = 0
    if 'INITIAL' in theme_info[theme]['steps'] and 'END INITIAL' in theme_info[theme]['steps']:
        pos = theme_info[theme]['steps'].index('END INITIAL') + 1
        initial_list = theme_info[theme]['steps'][theme_info[theme]['steps'].index('INITIAL') + 1: pos - 1]
    for i in range(len(theme_info[theme]['steps'][pos:])):
        step = theme_info[theme]['steps'][i + pos]
        if step not in ['LOOP', 'END LOOP']:
            steps.append(step)
        elif step == 'LOOP':
            if len(steps) > 0:
                steps_list.append(steps)
            steps = [step]
        else:
            steps.append(step)
            steps_list.append(steps)
            steps = []
    if len(steps) > 0:
        steps_list.append(steps)

    print('initial_list:', initial_list)

    # 定位其实位置: 逆序自检,从满足check函数的开始化简或求解
    # 有点小问题: 很难避免 每一步的Check函数都是唯一严格的,策略就是依次向后校验
    # 定位变成一组位置,从后向前直至找到解
    # 注意LOOP问题: 有异常或者全部check未通过才退出LOOP
    # 也可以放在生成steps_list之前定位,这里定位方便处理含有LOOP的模板
    # 2018-05-21 对于定位结果,新增初始化步骤
    #    初始化步骤是本模板必须运行的步骤,且只会出现在模板开始
    steps_list_list = []  # 一组定位结果
    i = len(steps_list)
    while i > 0:
        j = len(steps_list[i - 1])
        while j > 0:
            step = steps_list[i - 1][j - 1]
            print('expr', expr)
            try:
                if step not in ['LOOP', 'END LOOP'] and step_info[step]['check_func'](expr):
                    print('定位:', step)
                    # if steps_list[i - 1][0] != 'LOOP':
                    #     steps_list[i - 1] = steps_list[i - 1][j-1:]
                    #
                    # # 截取最后的steps
                    # steps_list = steps_list[i - 1:]
                    steps_list_list.append(steps_list[i - 1:])
                    if steps_list[i - 1][0] != 'LOOP':
                        steps_list_list[-1][0] = steps_list_list[-1][0][j-1:]

                    # 退出循环
                    j = 0
                    # i = 0
            except:
                error = ' '.join(['expr:', str(expr), 'check函数:', step, '异常 at Line:',
                                  str(sys.exc_info()[-1].tb_lineno), str(sys.exc_info())])
                print(error)
                log_info.append(error)
            j -= 1
        i -= 1

    # 根据initial_list 统一合并
    if len(initial_list) > 0:
        for steps_list in steps_list_list:
            steps_list.insert(0, initial_list)

    print('steps_list_list:', steps_list_list)

    expr_origin = expr
    for steps_list in steps_list_list:
        rst = []
        print('gen steps_list:', steps_list)
        expr = expr_origin
        i = 0
        while i < len(steps_list):
        # for i in range(len(steps_list)):
            steps = steps_list[i]
            # LOOP循环块
            if steps[0] == 'LOOP':
                finished = False
                loop_cnt = 0
                while not finished:
                    # 为了暂时预防返回desc异常,循环次数最多5次
                    loop_cnt += 1
                    if loop_cnt > 5:
                        break
                    # 有效解题步骤数
                    eff_steps = 0
                    for j in range(len(steps[1: len(steps)-1])):
                    # while j < len(steps[1: len(steps)-1]):
                        step = steps[1: len(steps)-1][j]
                        # print(step, expr, step_info[step]['check_func'](expr))
                        try:
                            if step_info[step]['check_func'](expr):
                                # 对于LOOP块中的任何一块,只要返回desc=None,则步骤结束,退出循环块
                                # print(expr, step_info[step]['core_func'](expr))
                                try:
                                    for rst_this in step_info[step]['core_func'](expr):
                                        if rst_this['desc'] is not None:
                                            rst.append(rst_this)
                                            # 更新expr
                                            expr = rst_this['expr']
                                            # print('loop i:', i, len(steps_list))
                                            # print('loop j:', j, len(steps))
                                            # 模板最后一步
                                            # if j == len(steps[1: len(steps)-1]) - 1 and i == len(steps_list) - 1:
                                            #     end_flag = True
                                            # elif is_end_expr(expr):
                                            #     end_flag = True
                                            if is_end_expr(expr):
                                                end_flag = True
                                            # 成功经过处理 +1
                                            eff_steps += 1
                                        # else:
                                        #     finished = True
                                        #     break
                                except:
                                    # 调用的函数有异常,退出此方案
                                    error = ' '.join(['expr:', str(expr), '基本函数:', step, '异常 at Line:',
                                                      str(sys.exc_info()[-1].tb_lineno), str(sys.exc_info())])
                                    print(error)
                                    log_info.append(error)
                                    finished = True
                                    i = len(steps_list)
                                    break
                            # else:
                            #     # 不能通过自检,则循环块结束
                            #     finished = True
                            #     break
                        except:
                            error = ' '.join(['expr:', str(expr), 'check函数:', step, '异常 at Line:',
                                              str(sys.exc_info()[-1].tb_lineno), str(sys.exc_info())])
                            print(error)
                            log_info.append(error)
                            finished = True
                            break

                    if not finished and eff_steps == 0:
                        finished = True
            # 正常步骤
            else:
                for j in range(len(steps)):
                    step = steps[j]
                    # 通过自检函数
                    print('check_func expr:', expr)
                    try:
                        if step_info[step]['check_func'](expr):
                            # 返回的desc,None视为没无需运行,已是此函数最简形式
                            try:
                                # print('core_func', step, step_info[step]['core_func'](expr))
                                for rst_this in step_info[step]['core_func'](expr):
                                    if rst_this['desc'] is not None:
                                        rst.append(rst_this)
                                        # 更新expr
                                        expr = rst_this['expr']
                                        # print('i:', i, len(steps_list))
                                        # print('j:', j, len(steps))
                                        # 模板最后一步
                                        # if j == len(steps) - 1 and i == len(steps_list) - 1:
                                        #     end_flag = True
                                        # elif is_end_expr(expr):
                                        #     end_flag = True
                                        if is_end_expr(expr):
                                            end_flag = True
                            except Exception as e:
                                # 调用的函数有异常,退出此方案
                                error = ' '.join(['expr:', str(expr), '基本函数:', step, '异常 at Line:',
                                                  str(sys.exc_info()[-1].tb_lineno), str(sys.exc_info())])
                                print(error)
                                log_info.append(error)
                                # print('step:', step, '异常', sys.exc_info())
                                # # logger.error(' '.join(['step:', step, '异常', str(sys.exc_info())]))
                                # log_info.append(' '.join(['step:', step, '异常', str(sys.exc_info())]))
                                # print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
                                i = len(steps_list)
                                break
                    except Exception as e:
                        error = ' '.join(['expr:', str(expr), 'check函数:', step, '异常 at Line:',
                                          str(sys.exc_info()[-1].tb_lineno), str(sys.exc_info())])
                        print(error)
                        log_info.append(error)
                        # break
            i += 1
        # 逆序直至找到解
        if end_flag:
            break
                    # except:
                    #     print('expr--', expr, 'step:', step, 'check_func:', step_info[step]['check_func'](expr))
                    #     print(sys.exc_info())
    # print('rst::::::', rst)
    print('end_flag:', end_flag)
    return rst, end_flag


def theme_solvers(expr, expr_element):
    """
    基于模板求解
    化简或求解一个代数式或等式
    :param expr:
        sympy表达式
    :param expr_element:
        表达式所属数学元素
    :return:
        data.frame
        name: result
        columns:
            desc: 描述,
            expr: 中间结果
    """
    global theme_info, step_info, element_relations, log_info, debug
    result_df = pd.DataFrame()

    desc_list = []
    expr_list = []
    theme_list = []
    end_list = []
    for theme_name in theme_info:
        # if expr_element in theme_info[theme_name]['input_elements']:
        # 节点或者父节点在模板里即可
        # print(expr_element, element_relations[expr_element])
        # print(theme_info[theme_name]['input_elements'])
        expr_element_set = element_relations[expr_element]
        expr_element_set.update([expr_element])
        if len(expr_element_set.intersection(set(theme_info[theme_name]['input_elements']))) > 0:
            rst = atom_theme_solvers(expr, theme_name)
            print('theme_name:', theme_name, rst[1])
            desc_list_this = []
            expr_list_this = []
            theme_list_this = []
            end_list_this = []
            try:
                if debug:
                    for step in rst[0]:
                        desc_list_this.append(step['desc'])
                        expr_list_this.append(''.join(['$', str(latex(step['expr'])), '$']))
                        theme_list_this.append(theme_name)
                        end_list_this.append(rst[1])
                elif rst[1]:
                    for step in rst[0]:
                        desc_list_this.append(step['desc'])
                        expr_list_this.append(''.join(['$', str(latex(step['expr'])), '$']))
                        theme_list_this.append(theme_name)
                        end_list_this.append(rst[1])

                # 如果找到能求出解的模板,则退出
                # if rst[1]:
                #     break
            except:
                error = ' '.join(['expr:', str(expr), '模板名称:', theme_name, '基本函数:', str(step),'异常 at Line:',
                                  str(sys.exc_info()[-1].tb_lineno), str(sys.exc_info())])
                print(error)
                log_info.append(error)
                desc_list_this = []
                expr_list_this = []
                theme_list_this = []
                end_list_this = []
            desc_list.extend(desc_list_this)
            expr_list.extend(expr_list_this)
            theme_list.extend(theme_list_this)
            end_list.extend(end_list_this)

    result_df['desc'] = desc_list
    result_df['expr'] = expr_list
    result_df['theme'] = theme_list
    result_df['end'] = end_list
    return result_df


def auto_solvers(expr, expr_element):
    """
    自动化求解
    化简或求解一个代数式或等式
    :param expr:
        sympy表达式
    :param expr_element:
        表达式所属数学元素
    :return:
        data.frame
        name: result
        columns:
            desc: 描述,
            expr: 中间结果
    """
    pass


def get_expr_graph(expr):
    """
    :param expr:
        sympy表达式
    :return:
        data.frame
        name: graph
        columns:
            from: 父节点,
            from_attr: 父节点属性即所属数学元素,
            to: 子节点,
            to_attr: 子节点属性即所属数学元素
            edge_attr: 节点属性即对应数学操作符
    """
    graph_df = pd.DataFrame()
    expr_graph = expr2graph(expr, 1)
    er = ElementRecognition(expr_graph)
    er.set_elements()

    # 解析图
    par_nodes = []
    par_attrs = []
    child_nodes = []
    child_attrs = []
    edge_attrs = []
    sorted_nodes = list(nx.topological_sort(expr_graph))
    for node in sorted_nodes:
        for child in expr_graph.successors(node):
            par_nodes.append(node)
            par_attrs.append(expr_graph.node[node]['attr_dict']['element'])
            child_nodes.append(child)
            child_attrs.append(expr_graph.node[child]['attr_dict']['element'])
            edge_attrs.append(expr_graph.get_edge_data(node, child)['attr_dict']['rel'])
    graph_df['from'] = par_nodes
    graph_df['from_attr'] = par_attrs
    graph_df['to'] = child_nodes
    graph_df['to_attr'] = child_attrs
    graph_df['edge_attr'] = edge_attrs

    # 求解或化简, 先按照模板求解
    expr_element = expr_graph.node[sorted_nodes[0]]['attr_dict']['element']
    print('get_expr_graph,expr_element:', expr_element)
    return graph_df, expr_element


def atom_solvers(expr):
    """
        化简或求解一个代数式或等式
        expr:
            sympy表达式
        :return
        data.frame
        name: result
        columns:
            desc: 描述,
            expr_txt: 中间结果
    """
    expr_graph = get_expr_graph(expr)
    result_df = theme_solvers(expr, expr_graph[1])
    return [result_df, expr_graph[0]]


def solvers(expr_list):
    """
    expr_list:
        [expr1, expr2, ...]
        expr1: sympy表达式
    :return
        data.frame1
        name: result
        columns:
            id: 习题ID,
            desc: 描述,
            expr_txt: 中间结果

        data.frame2
        name: graph
        columns:
            id: 习题ID,
            from: 父节点,
            from_attr: 父节点属性即所属数学元素,
            to: 子节点,
            to_attr: 子节点属性即所属数学元素
            edge_attr: 节点属性即对应数学操作符
    """
    global log_info
    result_df = pd.DataFrame()
    graph_df = pd.DataFrame()
    for i in range(len(expr_list)):
        problem_id = i + 1
        rst = atom_solvers(expr_list[i])
        # print('原子求解:', expr_list[i], rst[0])
        rst[0]['id'] = [problem_id] * len(rst[0])
        rst[1]['id'] = [problem_id] * len(rst[1])
        result_df = result_df.append(rst[0])
        graph_df = graph_df.append(rst[1])
    # print('result_df:', result_df)
    # print('graph_df:', graph_df)
    return [result_df, graph_df, log_info]


def parse_txt_type(txt):
    txt_type = 'sympy'
    if '$' in txt:
        txt_type = 'body'
    elif '\\' in txt \
            or '=' in txt \
            or '>' in txt \
            or '<' in txt \
            or '^' in txt \
            or type(txt) is list:
        txt_type = 'latex'
    return txt_type


def huluwa_solvers(expr_txt, txt_type='auto', debug_m=True):
    """
    :param expr_txt:
        需要求解的表达式,可能是单独的表达式,也可能是list形式,比如: 'x^2 + 3x + 8 = 9'或 '[x^2 + 3x + 8 = 9, y + x = 9]'
    :param txt_type:
        文本类型 latex/sympy/body
    :param debug_m:
        debug模式会返回所有模板结果,即便没有求得最终解
        非debug即正常模式,只返回有解的结果(下一步可以优化为只返回最优结果)
    :return:
    """
    global log_info, theme_info, step_info, element_relations, debug
    debug = debug_m
    # print('.....................------>', debug)
    # 解析方程组
    expr_txt = parse_expr_input(expr_txt)
    print('初始化模板信息......')
    get_theme_info()
    print('初始化解题步骤信息......')
    get_step_info()
    print('初始化数学元素关系图信息......')
    get_element_relations()
    log_info = []
    # import re
    if txt_type is 'auto':
        txt_type = parse_txt_type(expr_txt)
    print('txt_type:', txt_type)
    # txt_type = parse_txt_type(expr_txt)
    # print('txt_type:', txt_type)
    expr_list = []
    try:
        if txt_type == 'latex':
            if type(expr_txt) is list:
                expr_list = [[parse_expr(str(process_sympy(x)), evaluate=False) for x in expr_txt]]
            else:
                expr_list = [parse_expr(str(process_sympy(expr_txt)), evaluate=False)]
            # print('expr_list:', expr_list)
        if txt_type == 'sympy':
            if type(expr_txt) is list:
                expr_list = [[parse_expr(x, evaluate=False) for x in expr_txt]]
            else:
                expr_list = [parse_expr(expr_txt, evaluate=False)]
        if txt_type == 'body':
            expr_txt = expr_txt.replace('，', ',').replace('$,$', '').replace('$$', '')
            expr_txt = rex.sub('(<div>.*?</div>)', '', expr_txt)
            r1 = '\\$(.*?)\\$'
            latex_list = rex.findall(r1, expr_txt)
            a = Alegbra(latex_list)
            a.filter()
            a.fmt()
            a.sympy_check()
            expr_list = a.expr_list
    except:
        error = ' '.join(['huluwa_solvers expr:', expr_txt, '异常 at Line:',
                          str(sys.exc_info()[-1].tb_lineno), str(sys.exc_info())])
        print(error)
        log_info.append(error)
    return solvers(expr_list)


def parse_expr_input(expr_txt):
    exprs = expr_txt.strip()
    expr_txt = expr_txt.strip()
    if expr_txt.startswith('[') and expr_txt.endswith(']'):
        exprs = []
        for sub in expr_txt[1: -1].split(','):
            exprs.append(sub.strip())
    # print('expr_txt:', expr_txt)
    return exprs


def test(expr_txt):
    # print('huluwa_solvers:', huluwa_solvers('x^2 + 4 = 8 + x'))
    # print('huluwa_solvers:', huluwa_solvers('x^2 + 2*x + 1 = 0'))
    print('huluwa_solvers:', huluwa_solvers(expr_txt))
    # print('huluwa_solvers:', huluwa_solvers('3 * x ^ 2 + 5 * x + 5 = 0'))


# if __name__ == '__main__':
#     test(sys.argv[1])
#     try:
#         expr_txt = None
#         if len(sys.argv) > 1:
#             expr_txt = sys.argv[1]
#         if expr is not None:
#             test(expr_txt)
#     except:
#         pass
