# encoding: utf-8
"""
公共函数库,基础函数
default interpreter: python3
Created on 2018-04-13
"""


def get_denominator(expr,x = symbols('x')):
    denominator = None
    if expr.func.__name__ == 'Pow' and expr.args[1] == -1:
            return expr.args[0]
    if expr.func.__name__ == 'Mul':
        for sub_expr in expr.args:
            if sub_expr.func.__name__ == 'Pow' and sub_expr.args[1] == -1:
                return sub_expr.args[0]
    return denominator
