# encoding: utf-8
"""
解析Sympy表达式,转换为Neo4j图对象形式
    1,节点为表达式
    2,节点属性包含数学元素
    3,节点之间以操作符表达关系
    4,该图为下一步自动解题的输入形式
default interpreter: python3
Created on 2018-04-13
@author: wangguojie
"""
import os, sys
print(os.getcwd())
sys.path.append(os.getcwd())
import networkx as nx
from sympy import *
from element_recognition import *
import CustomeOperator


def expr2graph(expr, code):
    """
    code: 当前节点编号,如:1.2、2.3.1
    新增支持方程组 2018-05-22
    节点命名:
        "父节点编号.横向位置"
        比如父节点编号为3.2，横向位置为3的节点可以写作:3.2.3
    """
    graph = nx.DiGraph()
    par_node = ' '.join([str(code), str(expr)])
    children = get_children(expr, code, par_node, 0)
    graph = nx.compose(graph, children)
    # print('graph nodes:', graph.nodes())
    # print('graph edges:', graph.edges())
    # for child in nx.descendants(graph, par_node):
    for child in graph.successors(par_node):
        # 基础Sympy字符或常量,不再拆解
        # print('nodes:', child, graph.node[child])
        if not isinstance(graph.node[child]['attr_dict']['func'], Atom):
            graph = nx.compose(graph, expr2graph(graph.node[child]['attr_dict']['expr'],
                                                 graph.node[child]['attr_dict']['code']))
    return graph


def get_children(expr, code, par_node, index):
    """
        新增支持方程组 2018-05-22
        还原减法和除法,获得当前表达式对应的子节点
            1,多项(>2)加减
            2,减法问题
        直接按照人的理解拆解成图
        返回的是一个2层深度的子图,父节点为当前表达式,子节点为其子表达式
        节点:
            名称: 编号+表达式名称，其中父节点名称即为 code + ' ' + str(expr)
        边:
            操作符: Add,Sub,Mul,Div,Sqrt等
        paras:
            expr: SymPy 表达式
            code: 父节点编码 str
            par_node: 父节点名称 str
            index: 父节点包含子节点已经编码的位置
    """
    graph = nx.DiGraph()
    if type(expr) is not list:
        graph.add_node(par_node, attr_dict={'expr': expr,
                                            'code': str(code),
                                            'func': expr.func})
        # print('get_children:', expr, expr.func)
        if expr.is_Add:
            for i in range(len(expr.args)):
                item = expr.args[i]
                if item.is_Add:
                    graph = nx.compose(graph, get_children(item, code, par_node, index))
                    index = len(graph.nodes()) - 1
                elif item.is_Mul:
                    # 只要有负数出现,即为减法运算
                    has_negative = False
                    this_args = list(item.args)
                    for j in range(len(item.args)):
                        e = item.args[j]
                        if e.is_negative:
                            has_negative = True
                            this_args[j] = abs(e)
                        break
                    if has_negative:
                        # 负数 变成减法运算
                        item = None
                        for e in this_args:
                            if item is None:
                                item = e
                            else:
                                item = Mul(item, e, evaluate=False)
                        this_code = ''.join([str(code), '.', str(index + 1)])
                        this_node = ''.join([this_code, ' ', str(item)])
                        graph.add_node(this_node, attr_dict={'expr': item,
                                                             'code': this_code,
                                                             'func': item.func})
                        graph.add_edge(par_node, this_node, attr_dict={'rel': 'Sub',
                                                                       'rel_func': CustomeOperator.sub})
                        index += 1
                    else:
                        this_code = ''.join([str(code), '.', str(index + 1)])
                        this_node = ''.join([this_code, ' ', str(item)])
                        graph.add_node(this_node, attr_dict={'expr': item,
                                                             'code': this_code,
                                                             'func': item.func})
                        graph.add_edge(par_node, this_node, attr_dict={'rel': expr.func.__name__,
                                                                       'rel_func': expr.func})
                        index += 1
                elif item.is_negative:
                    # 负数 变成减法运算
                    item = abs(item)
                    this_code = ''.join([str(code), '.', str(index + 1)])
                    this_node = ''.join([this_code, ' ', str(item)])
                    graph.add_node(this_node, attr_dict={'expr': item,
                                                         'code': this_code,
                                                         'func': item.func})
                    graph.add_edge(par_node, this_node, attr_dict={'rel': 'Sub',
                                                                   'rel_func': CustomeOperator.sub})
                    index += 1
                else:
                    this_code = ''.join([str(code), '.', str(index + 1)])
                    this_node = ''.join([this_code, ' ', str(item)])
                    graph.add_node(this_node, attr_dict={'expr': item,
                                                         'code': this_code,
                                                         'func': item.func})
                    graph.add_edge(par_node, this_node, attr_dict={'rel': expr.func.__name__,
                                                                   'rel_func': expr.func})
                    index += 1
        elif expr.is_Mul:
            for i in range(len(expr.args)):
                item = expr.args[i]
                if item.is_Mul:
                    graph = nx.compose(graph, get_children(item, code, par_node, index))
                    index = len(graph.nodes()) - 1
                elif item.is_Pow and item.args[1] == -1:
                    this_code = ''.join([str(code), '.', str(index + 1)])
                    this_node = ''.join([this_code, ' ', str(item.args[0])])
                    graph.add_node(this_node, attr_dict={'expr': item.args[0],
                                                         'code': this_code,
                                                         'func': item.func})
                    graph.add_edge(par_node, this_node, attr_dict={'rel': 'Div',
                                                                   'rel_func': CustomeOperator.div})
                    index += 1
                else:
                    this_code = ''.join([str(code), '.', str(index + 1)])
                    this_node = ''.join([this_code, ' ', str(item)])
                    graph.add_node(this_node, attr_dict={'expr': item,
                                                         'code': this_code,
                                                         'func': item.func})
                    graph.add_edge(par_node, this_node, attr_dict={'rel': expr.func.__name__,
                                                                   'rel_func': expr.func})
                    index += 1
        elif expr.is_Pow:
            # 标注底
            base_code = ''.join([str(code), '.', str(index + 1)])
            base_node = ''.join([base_code, ' ', str(expr.args[0])])
            graph.add_node(base_node, attr_dict={'expr': expr.args[0],
                                                 'code': base_code,
                                                 'func': expr.args[0].func})
            graph.add_edge(par_node, base_node,
                           attr_dict={'rel': 'pow_base', 'rel_func': expr.func})

            # 标注幂
            power_code = ''.join([str(code), '.', str(index + 2)])
            power_node = ''.join([power_code, ' ', str(expr.args[1])])
            graph.add_node(power_node, attr_dict={'expr': expr.args[1],
                                                  'code': power_code,
                                                  'func': expr.args[1].func})
            graph.add_edge(par_node, power_node,
                           attr_dict={'rel': 'pow_power', 'rel_func': expr.func})
        else:
            rel = expr.func
            for i in range(len(expr.args)):
                item = expr.args[i]
                this_code = ''.join([str(code), '.', str(index + 1)])
                this_node = ''.join([this_code, ' ', str(item)])
                graph.add_node(this_node, attr_dict={'expr': item,
                                                     'code': this_code,
                                                     'func': item.func})
                graph.add_edge(par_node, this_node, attr_dict={'rel': rel.__name__, 'rel_func': rel})
                index += 1
    else:
        # 处理组合问题,暂时只解析方程组问题
        graph.add_node(par_node, attr_dict={'expr': expr,
                                            'code': str(code),
                                            'func': CustomeOperator.contains})
        for i in range(len(expr)):
            item = expr[i]
            this_code = ''.join([str(code), '.', str(index + 1)])
            this_node = ''.join([this_code, ' ', str(item)])
            graph.add_node(this_node, attr_dict={'expr': item,
                                                 'code': this_code,
                                                 'func': item.func})
            graph.add_edge(par_node, this_node, attr_dict={'rel': 'contains', 'rel_func': CustomeOperator.contains})
            index += 1
    return graph


def set_node_elements(graph):
    """
        设置graph上节点包含的数学元素或基础数据类型
        从底而上
    """
    nodes = list(reversed(list(nx.topological_sort(graph))))


class Graph2Expr:
    """
        还原一张图至Sympy表达式
        只针对2层深度的子图
        用于反向求解更新图
    """
    def __init__(self, graph):
        self.graph = graph
        self.expr = None

    def _add(self):
        self

    def _sub(self):
        self

    def mul(self):
        self

    def div(self):
        self


def test():
    import os
    import sys
    sys.path.append(os.path.join(os.path.expanduser("~"), "git/latex2sympy"))
    from process_latex import process_sympy
    from sympy.parsing.sympy_parser import parse_expr
    # latex = "5xy - (2 + x)/3 - 9 = 8"
    # latex = '(-1.5) \\div \\frac{1}{9}'
    # latex = '2/6 + 3/7'
    # latex = 'x^2 + 2*x + 1 = 0'
    s1 = process_sympy('x + y = 4')
    s1 = parse_expr(str(s1), evaluate=False)
    s2 = process_sympy('x + 2x + 1 = 0')
    s2 = parse_expr(str(s2), evaluate=False)
    s3 = process_sympy('x + 2z + 1 = 0')
    s3 = parse_expr(str(s3), evaluate=False)
    s = [s1, s2, s3]
    # s = parse_expr(str(process_sympy('x + y = 4')), evaluate=False)
    # print('\nlatex:', latex, '\nsympy:', s)
    print('sympy exprs:', s)
    graph_test = expr2graph(s, 1)
    print(graph_test.nodes())
    print(graph_test.edges())
    print('graph_test graph:', list(reversed(list(nx.topological_sort(graph_test)))))
    er = ElementRecognition(graph_test)
    er.set_elements()
    print('graph_test elements:', list(reversed(list(nx.topological_sort(graph_test)))))
    for node in list(nx.topological_sort(graph_test)):
        print('node:', node, 'attr:', graph_test.node[node])
        for child in graph_test.successors(node):
            print('child:', child, graph_test.get_edge_data(node, child))
        print()
    return list(reversed(list(nx.topological_sort(graph_test))))


if __name__ == '__main__':
    test()



