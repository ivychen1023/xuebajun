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
for dat in mi['solutions_themes'].find({}):
    name = dat['name']
    theme_info_this = dict()
    theme_info_this['input_elements'] = dat['input_elements'].split(', ')
    theme_info_this['steps'] = dat['steps'].split(', ')
    theme_info[name] = theme_info_this
print('theme_info:', theme_info)


# 解题步骤相关信息
# name, input_elements, output_elements, check_func, core_func, type
step_info = dict()
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
        pass
print('step info:', step_info)

element_relations = dict()
for dat in list(mi['elements'].find()):
    if dat['element'] in element_relations:
        element_relations[dat['element']].update([dat['par_element']])
    else:
        element_relations[dat['element']] = set([dat['par_element']])


def theme_solvers(expr, theme):
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
    for step in theme_info[theme]['steps']:
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

    # 定位其实位置: 逆序自检,从满足check函数的开始化简或求解
    # 有点小问题: 很难避免 每一步的Check函数都是唯一严格的,策略就是依次向后校验
    # 定位变成一组位置,从后向前直至找到解
    # 注意LOOP问题: 正常情况下,只需Check LOOP第一项即可
    # 也可以放在生成steps_list之前定位,这里定位方便处理含有LOOP的模板
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
                    # # 非循环list截取,理论上讲,再LOOP内,后面的能通过自检,前面的必然能通过自检
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
                while not finished:
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
                                            if j == len(steps[1: len(steps)-1]) - 1 and i == len(steps_list) - 1:
                                                end_flag = True
                                        else:
                                            finished = True
                                            break
                                except:
                                    # 调用的函数有异常,退出此方案
                                    error = ' '.join(['expr:', str(expr), '基本函数:', step, '异常 at Line:',
                                                      str(sys.exc_info()[-1].tb_lineno), str(sys.exc_info())])
                                    print(error)
                                    log_info.append(error)
                                    finished = True
                                    i = len(steps_list)
                                    break
                            else:
                                # 不能通过自检,则循环块结束
                                finished = True
                                break
                        except:
                            error = ' '.join(['expr:', str(expr), 'check函数:', step, '异常 at Line:',
                                              str(sys.exc_info()[-1].tb_lineno), str(sys.exc_info())])
                            print(error)
                            log_info.append(error)
                            finished = True
                            break
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
                                        if j == len(steps) - 1 and i == len(steps_list) - 1:
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


def atom_solvers(expr):
    """
        化简或求解一个代数式或等式
        expr: sympy表达式
        :return
        data.frame1
        name: result
        columns:
            desc: 描述,
            expr_txt: 中间结果

        data.frame2
        name: graph
        columns:
            from: 父节点,
            from_attr: 父节点属性即所属数学元素,
            to: 子节点,
            to_attr: 子节点属性即所属数学元素
            edge_attr: 节点属性即对应数学操作符
    """
    global theme_info, step_info, element_relations, log_info
    result_df = pd.DataFrame()
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
    print('atom_solvers,expr_element:', expr_element)

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
            print('theme_name:', theme_name)
            rst = theme_solvers(expr, theme_name)
            desc_list_this = []
            expr_list_this = []
            theme_list_this = []
            end_list_this = []
            try:
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
    return [result_df, graph_df]


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
            or '^' in txt:
        txt_type = 'latex'
    return txt_type


def huluwa_solvers(expr_txt, txt_type='auto'):
    global log_info
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
            expr_list = [parse_expr(str(process_sympy(expr_txt)), evaluate=False)]
        if txt_type == 'sympy':
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
        error = ' '.join(['expr:', expr_txt, '异常 at Line:',
                          str(sys.exc_info()[-1].tb_lineno), str(sys.exc_info())])
        print(error)
        log_info.append(error)
    return solvers(expr_list)


def test(expr_txt):
    # print('huluwa_solvers:', huluwa_solvers('x^2 + 4 = 8 + x'))
    # print('huluwa_solvers:', huluwa_solvers('x^2 + 2*x + 1 = 0'))
    print('huluwa_solvers:', huluwa_solvers(expr_txt))
    # print('huluwa_solvers:', huluwa_solvers('3 * x ^ 2 + 5 * x + 5 = 0'))


# if __name__ == '__main__':
#     try:
#         expr_txt = None
#         if len(sys.argv) > 1:
#             expr_txt = sys.argv[1]
#         if expr is not None:
#             test(expr_txt)
#     except:
#         pass
