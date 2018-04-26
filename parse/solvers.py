# encoding: utf-8
"""
自动解题
default interpreter: python3
Created on 2018-04-25
@author: wangguojie
"""
import os
import sys
sys.path.append(os.path.join(os.path.expanduser("~"), "git/latex2sympy"))
sys.path.append('')

import pandas as pd
import networkx as nx
from pymongo import MongoClient
from process_latex import process_sympy
from sympy.parsing.sympy_parser import parse_expr
from sts_algebra import Alegbra
from element_recognition import ElementRecognition
from parse import expr2graph
from sympy import latex


# mi数据库
mi = MongoClient(host="10.8.8.71", connect=False)['mi']

import re
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
        func_name = re.findall('def(.*)\\(', dat['func'])[0].strip(' ')
        step_info_this['core_func'] = eval(func_name)
        dat['check'] = dat['check'].replace(' check(', ''.join([' ', func_name, '_check(']))
        exec(dat['check'])
        step_info_this['check_func'] = eval(re.findall('def(.*)\\(', dat['check'])[0].strip(' '))
        step_info_this['type'] = dat['type']
        name = dat['name']
        step_info[name] = step_info_this
    except:
        pass

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
    global step_info, theme_info
    rst = []
    end_flag = False
    # 逆序自检,从满足check函数的开始化简或求解
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
    # print('steps_list:', steps_list)
    for steps in steps_list:
        # LOOP循环块
        if steps[0] == 'LOOP':
            finished = False
            while not finished:
                for step in steps[1: len(steps)-1]:
                    # print(step, expr, step_info[step]['check_func'](expr))
                    if step_info[step]['check_func'](expr):
                        # 对于LOOP块中的任何一块,只要返回desc=None,则步骤结束,退出循环块
                        print(expr, step_info[step]['core_func'](expr))
                        for rst_this in step_info[step]['core_func'](expr):
                            if rst_this['desc'] is not None:
                                rst.append(rst_this)
                                # 更新expr
                                expr = rst_this['expr']
                            else:
                                finished = True
                                break
                    else:
                        # 不能通过自检,则循环块结束
                        finished = True
                        break
        # 正常步骤
        else:
            for step in steps:
                # 通过自检函数
                print('check_func expr:', expr)
                try:
                    if step_info[step]['check_func'](expr):
                        # 返回的desc不能为None,None视为没有运行
                        print('core_func', step, step_info[step]['core_func'](expr))
                        for rst_this in step_info[step]['core_func'](expr):
                            if rst_this['desc'] is not None:
                                rst.append(rst_this)
                                # 更新expr
                                expr = rst_this['expr']
                except:
                    print('expr--', expr)
    # print('rst::::::', rst)
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
    global theme_info, step_info, element_relations
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
    for theme_name in theme_info:
        # if expr_element in theme_info[theme_name]['input_elements']:
        # 节点或者父节点在模板里即可
        print(expr_element, element_relations[expr_element])
        print(theme_info[theme_name]['input_elements'])
        expr_element_set = element_relations[expr_element]
        expr_element_set.update([expr_element])
        if len(expr_element_set.intersection(set(theme_info[theme_name]['input_elements']))) > 0:
            print('theme_name:', theme_name)
            rst = theme_solvers(expr, theme_name)
            # if rst[1]:
            for step in rst[0]:
                desc_list.append(step['desc'])
                expr_list.append(''.join(['$', str(latex(step['expr'])), '$']))
            break
    result_df['desc'] = desc_list
    result_df['expr'] = expr_list
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
    return [result_df, graph_df]


def parse_txt_type(txt):
    txt_type = 'sympy'
    if '$' in txt:
        txt_type = 'body'
    elif '\\' in txt or '=' in txt or '>' in txt or '<' in txt:
        txt_type = 'latex'
    return txt_type


def huluwa_solvers(expr_txt, txt_type='auto'):
    import re
    if txt_type is 'auto':
        txt_type = parse_txt_type(expr_txt)
    print('txt_type:', txt_type)
    expr_list = []
    if txt_type == 'latex':
        expr_list = [process_sympy(expr_txt)]
    if txt_type == 'sympy':
        expr_list = [parse_expr(expr_txt, evaluate=False)]
    if txt_type == 'body':
        expr_txt = expr_txt.replace('，', ',').replace('$,$', '').replace('$$', '')
        expr_txt = re.sub('(<div>.*?</div>)', '', expr_txt)
        r1 = '\\$(.*?)\\$'
        latex_list = re.findall(r1, expr_txt)
        a = Alegbra(latex_list)
        a.filter()
        a.fmt()
        a.sympy_check()
        expr_list = a.expr_list
    return solvers(expr_list)


def test():
    # print('huluwa_solvers:', huluwa_solvers('x^2 + 4 = 8 + x'))
    print('huluwa_solvers:', huluwa_solvers('x^2 + 2*x + 1 = 0'))

if __name__ == '__main__':
    test()
