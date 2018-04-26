# encoding: utf-8
"""
1, 统计代数式/等式/方程/不等式:
    1.1 Txt --> Latex --> SymPy --> Sts
2,主要发现:
    2.1 代数式:
        2.1.1 主线运算
            2.1.1.1 Add、Sub、Mul、Div、Power、Sqrt
        2.1.2 主线元素代数式类型
            2.1.2.1 有理式
                2.1.2.1.1 整式(单项式、多项式)
                    2.1.2.1.1.1 单项式仅指含有字母，子term不能包含Mul
                    2.1.2.1.1.2 多项式仅指含有上述单项式
                2.1.2.1.2 分式
                    2.1.2.1.2.1  此处仅指分子|分母 含有字母的代数式
            2.1.2.2 无理式
                2.1.2.2.1 含有字母的根式
    2.2 不等式
        2.2.1 必须包含变量,不考虑类似于条件的约束
    2.3 等式
        2.3.1 方程
        2.3.2 函数
            y = expression
3,Note:
    3.1 Latex --> SymPy
        3.1.1 \frac --> \\frac、
              \times --> \\times、
              \leqslant --> <= 、
              \geqslant --> >=
              ......
        3.1.2 () 直接与字符相连,会当成函数
        3.1.3 = 右边必须有值
        3.1.4 转换之后的SymPy,srepr深度优先,
              转换之后(srepr(eval(str(expr))))为广度优先,方便拿到自然层次结构,需要默认所有字符为Symbol
    3.2 Txt --> Latex
        3.2.1 连续的$可以合并
        3.2.2 只要单个式子,式子组先忽略
    3.3 标注规则
        3.3.1 优先标记子Label
        3.3.2 如果标注Label文本或其父Label已经出现,则忽略
        3.3.3 当标注很多时,选取相对权重较高的
    3.4 Tips
        3.4.1 不处理包含几何操作符的习题
        3.4.2 trim '='
        3.4.3 括号直接与字母连接,加乘法运算符
4,Todo
    4.1 支持方程组
    4.2 拿到解题步骤
default interpreter: python3
Created on 2018-03-21
@author: wangguojie
"""
import os
import sys
sys.path.append(os.path.join(os.path.expanduser("~"), "git/latex2sympy"))

import datetime
from sympy import *

from pymongo import MongoClient
from process_latex import process_sympy


import re
import pandas as pd
from sympy import *


class Alegbra:
    """
    解析代数式并进行标注
    """
    def __init__(self,
                 expr_list,
                 alegbra_operators=set(pd.read_csv('table/mathjax_alegbra.txt', header=-1)[0]),
                 geometry_operators=set(pd.read_csv('table/mathjax_geometry.txt', header=-1)[0]),
                 equation_operators=set(pd.read_csv('table/mathjax_equation.txt', header=-1)[0]),
                 nlp_noise=set(pd.read_csv('table/nlp_noise.txt', header=-1)[0])):
        self.expr_list = expr_list
        self.alegbra_operators = alegbra_operators
        self.geometry_operators = geometry_operators
        self.equation_operators = equation_operators
        self.nlp_noise = nlp_noise
        self.labels = []

    # 过滤MathJax表达式干扰项
    # 必须包含一个操作符
    # 包括几何操作符,此题不再处理
    def filter(self):
        expr_tmp_list = []
        contain_geometry_t = False
        for expr in self.expr_list:
            # 去除尾部干扰
            expr = expr.strip(' ').strip('=').strip('.').strip(',').strip(';').strip(':')

            # 判断是否包含干扰字符
            contain_noise = False
            for noise in self.nlp_noise:
                if noise in expr:
                    contain_noise = True
                    break

            # 判断是否包含几何操作符
            contain_geometry = False
            for operator in self.geometry_operators:
                if operator in expr:
                    contain_geometry = True
                    contain_geometry_t = True
                    break

            # 判断是否包含代数操作符
            contain_alegbra = False
            for operator in self.alegbra_operators:
                if operator in expr:
                    contain_alegbra = True
                    break
            if not contain_noise and contain_alegbra and not contain_geometry:
                expr_tmp_list.append(expr)
        if contain_geometry_t:
            expr_tmp_list = []
        self.expr_list = expr_tmp_list

    # 格式转换
    # 括号与字母直接连接,加乘法运算符:
    #  1,小写字母且不能是操作符
    #  2,括号内必须是代数式
    # trim =/' '
    # cdots --> ''
    # \leqslant --> <
    # \geqslant --> >
    # \cdot --> *
    # Note: 暂时只支持严格的不等式
    def fmt(self):
        import re
        expr_tmp_list = []
        for i in range(len(self.expr_list)):
            expr = self.expr_list[i]
            expr = expr\
                .replace('\\geqslant', '>')\
                .replace('\\leqslant', '<')
            expr_tmp = ''
            try:
                start = 0
                for s in re.finditer('([a-z]+)\\(', expr):
                    indexes = s.span()
                    expr_tmp += expr[start: indexes[0]]
                    # 不是代数操作符且括号内是代数表达式
                    # print('w:', expr[indexes[0]: (indexes[1] - 1)])
                    if expr[indexes[0]: (indexes[1] - 1)] not in self.alegbra_operators \
                            and expr[indexes[0]: (indexes[1] - 1)] not in self.geometry_operators\
                            and self.is_alegbra(expr[indexes[1]: expr[indexes[1]:].index(')') + indexes[1]]):
                        expr_tmp += expr[indexes[0]: (indexes[1] - 1)] + '*' + expr[indexes[1] - 1]
                    else:
                        expr_tmp += expr[indexes[0]: indexes[1]]
                    start = indexes[1]
                    # print('index:', indexes, expr_tmp)
                expr_tmp += expr[start:]
            except:
                expr_tmp = ''
                print('\nexpr:', expr, '\n', str(sys.exc_info()))
            if expr_tmp != '':
                expr_tmp_list.append(expr_tmp)
        self.expr_list = expr_tmp_list

    # Sympy符号检测,过滤掉不能被解析的表达式
    def sympy_check(self):
        expr_tmp_list = []
        for expr in self.expr_list:
            try:
                process_sympy(expr)
                expr_tmp_list.append(expr)
            except:
                print("\n", "expr:", expr,
                      '\nprocess_sympy error:',
                      str(sys.exc_info()))
        self.expr_list = expr_tmp_list

    # 代数式判别
    # 包含代数式同时不包含等式相关因素
    # @classmethod
    def is_alegbra(self, expr):
        contain_alegbra = False
        contain_equation = False
        for operator in self.alegbra_operators:
            if operator in expr:
                contain_alegbra = True
                break
        for operator in self.equation_operators:
            if operator in expr:
                contain_equation = True
                break
        for operator in self.geometry_operators:
            if operator in expr:
                contain_equation = True
                break
        if contain_alegbra and not contain_equation:
            return True
        return False

    # 返回的标签
    # 运算符
    # 代数式类型
    def update_labels(self):
        pass


def extract_mathjax_expr():
    """
    提取MathJax表达式并进行化简预处理
    :return:
    """
    pass


def test():
    import re
    alegbra_operators = set(pd.read_csv('table/mathjax_alegbra.txt', header=-1)[0])
    geometry_operators = set(pd.read_csv('table/mathjax_geometry.txt', header=-1)[0])
    equation_operators = set(pd.read_csv('table/mathjax_equation.txt', header=-1)[0])
    nlp_noise = set(pd.read_csv('table/nlp_noise.txt', header=-1)[0])
    problems_info = MongoClient(host="localhost", connect=False)['knowledge_graph']['problems_info']
    cursor = problems_info.find({})
    cnt = 0
    total = 0
    for dat in cursor:
        total += 1
        dat = dat['body'].replace('，', ',').replace('$,$', '').replace('$$', '')
        dat = re.sub('(<div>.*?</div>)', '', dat)
        r1 = '\\$(.*?)\\$'
        expr_list = re.findall(r1, dat)
        a = Alegbra(expr_list, alegbra_operators, geometry_operators, equation_operators, nlp_noise)
        a.filter()
        filter = a.expr_list
        a.fmt()
        fmt = a.expr_list
        a.sympy_check()
        check = a.expr_list
        # 测试log
        # if len(check) != len(filter):
        #     print('\n', 'dat:', dat)
        #     print('filter:', filter)
        #     print('fmt:', fmt)
        #     print('check:', check)
        if len(check) > 0:
            print('\n', check, '\n', [process_sympy(expr) for expr in check])
        if len(a.expr_list) > 0:
            cnt += 1
    print('alegbra_operators:', alegbra_operators)
    print('geometry_operators:', geometry_operators)
    print('equation_operators:', equation_operators)
    print('nlp_noise:', nlp_noise)
    print('total:', total, ' cnt:', cnt)


if __name__ == '__main__':
    test()



