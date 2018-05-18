# encoding: utf-8
"""
公共函数库,基础函数
default interpreter: python3
Created on 2018-04-13
"""
from sympy import *


def get_denominator(expr, x=symbols('x')):
    denominator = None
    if expr.func.__name__ == 'Pow' and expr.args[1] == -1:
            return expr.args[0]
    if expr.func.__name__ == 'Mul':
        for sub_expr in expr.args:
            if sub_expr.func.__name__ == 'Pow' and sub_expr.args[1] == -1:
                return sub_expr.args[0]
    return denominator


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


def is_same_expression(expr_a, expr_b):
    """
    判断是否为相同表达式
    严格意义的字符串的相同,不是数学意义上的相同
    :param expr_a:
    :param expr_b:
    :return:
        True ;当字符串一致
        False ;Else
    """
    return str(expr_a) == str(expr_b)


def is_sum_simplify(expr):
    """
    表达式是否已经加法化简:
        所有位置的加法进行化简
        若表达式中某代数式可加法化简,则同时会进行可能的乘法化简但单独的分母加法可化简除外
    :param expr:
    :return:
    """
    from sympy.simplify.simplify import sum_simplify
    return is_same_expression(expr, sum_simplify(expr))


def is_simplify(expr):
    """
    表达式是否已经化简
    :param expr:
    :return:
    """
    return is_same_expression(expr, simplify(expr))


def is_not_frac_real(expr):
    """
    整体单项式
    表达式已经化简
    是个实数
    但不是分数
    :param expr:
    :return:
    """
    if (not expr.is_Add) \
            and is_simplify(expr) \
            and expr.is_real \
            and (get_denominator(expr) is None):
        return True
    return False



