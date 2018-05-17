# encoding: utf-8
"""
公共函数库,基础函数
default interpreter: python3
Created on 2018-04-13
"""
from sympy import *


def is_fractional_equation(expr, x=symbols('x')):
    """
    判断是否为分式方程
        1,等式
        2,分母含有未知量
    :param expr:
        sympy 表达式
    :param x:
        指定sympy变量名称
    :return:
        分式方程判定
    """
    # 判断等式
    if expr.is_Equality:
        # 等式右边化为0,Poly()展开,针对每一个表达式,只要有一个分母含有变量,则判定为分式表达式
        expr = Add(expr.args[0], -expr.args[1])
        # 表达式大于一个
        if expr.is_Add:
            for sub_expr in expr.args:
                denominator = get_denominator(sub_expr)
                if denominator is not None and max(Poly(denominator, x).degree_list()) > 0:
                    return True
        else:
            denominator = get_denominator(expr)
            if denominator is not None and max(Poly(denominator, x).degree_list()) > 0:
                return True

    return False
