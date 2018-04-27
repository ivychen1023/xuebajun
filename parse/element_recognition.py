# encoding: utf-8
"""
数学元素识别
以【MI平台.数学元素】为准
http://10.8.8.71:3838/users/shiny/mi/
Note：
    表达式图需要从最底层向上匹配数学元素，
    数学元素需要从上至下遍历,步步缩小范围,直至停止。
    这是需要优化的一个点
        1,方向之一就是借助expr.func 直接判别
default interpreter: python3
Created on 2018-04-12
@author: wangguojie
"""


from sympy import *
import networkx as nx
import re
from pymongo import MongoClient


class ElementRecognition:
    """
    设置数学元素的标准是根据MI数学元素取最小辖域数学元素
    暂时'等式' 等价于 '方程'
    """
    def __init__(self, expr_graph):
        """
        expr_graph: contain sub node
        """
        self.expr_graph = expr_graph
        self.latin_alphabet_re = '[a-z|A-Z]'
        self.element_relations = {}
        self._get_element_relations()

    def _get_element_relations(self):
        """
        数学元素关系图:
          key: 数学元素
          value: key对应父节点组
        """
        dat_list = list(MongoClient(host="10.8.8.71", connect=False)['mi']['elements'].find())
        for dat in dat_list:
            if dat['element'] in self.element_relations:
                self.element_relations[dat['element']].update([dat['par_element']])
            else:
                self.element_relations[dat['element']] = set([dat['par_element']])

    def set_elements(self):
        # 图节点 从底向上遍历
        nodes = list(reversed(list(nx.topological_sort(self.expr_graph))))
        element = None
        for node in nodes:
            # 关系式、代数式、实数
            if self.is_relational_expression(node):
                # 后代 successors self.expr_graph.successors(node)
                element = self.get_relational_element(node)
            elif self.is_algebraic_expression(node):
                element = self.get_algebraic_element(node)
            elif self.is_real_expression(node):
                element = self.get_real_element(node)
            else:
                # 如果三者都不是 异常
                print('无法识别的表达式:', self.expr_graph.node[node]['attr_dict']['expr'])
            # 更新node信息
            self.expr_graph.node[node]['attr_dict'].update({'element': element})
        return self.expr_graph

    def get_relational_element(self, node):
        # element = '关系式'
        expr = self.expr_graph.node[node]['attr_dict']['expr']
        if expr.is_Equality:
            # element = '等式' # 暂时不区分等式与方程
            element = '方程'
            # poly 判断元和次数
            degrees = poly(Add(expr.args[0], -expr.args[1])).degree_list()
            if len(degrees) == 1 and max(degrees) == 1:
                element = '一元一次方程'
            if len(degrees) == 1 and max(degrees) == 2:
                element = '一元二次方程'
            if len(degrees) == 2 and max(degrees) == 1:
                element = '二元一次方程'
        else:
            element = '不等式'
        return element

    def get_algebraic_element(self, node):
        element = '代数式'
        # 判断无理式和有理式
        # 叶节点不会是无理式,只会是整数或整式
        # 判断是否有子节点
        expr = self.expr_graph.node[node]['attr_dict']['expr']
        has_fraction = False
        has_flatten_operator = False # 含有 Add/Sub横向扩展符
        has_polynomial = False
        if len(list(self.expr_graph.successors(node))) > 0:
            # 子节点有无理式或者操作符能产生无理式,根号
            for child_node in self.expr_graph.successors(node):
                if self.expr_graph.node[child_node]['attr_dict']['element'] == '无理式':
                    element = '无理式'
                    break
                # 如果包含'Div'操作符且分母为整式,则标记为分式
                rel = self.expr_graph.get_edge_data(node, child_node)['attr_dict']['rel']
                child_element = self.expr_graph.node[child_node]['attr_dict']['element']
                if rel == 'Div' and self.check_elements(child_element, '整式'):
                    has_fraction = True
                # 判断包含Add或Sub操作
                if not has_flatten_operator:
                    if rel == 'Add' or rel == 'Sub':
                        has_flatten_operator = True
                # 判断是否为多项式
                if not has_polynomial:
                    if self.check_elements(child_element, '多项式'):
                        has_polynomial = True
            if element == '代数式':
                # power操作符化简之后,基含有字母,幂不是整数
                expr_s = simplify(expr)
                if expr_s.is_Pow and self.has_latin_alphabet(expr_s) and not expr_s.args[1].is_Rational:
                    element = '无理式'
            if element == '代数式':
                if has_fraction:
                    element = '分式'
                else:
                    # 含有多项但每一项都是单项式且是乘积的关系,定为单项式
                    if not has_flatten_operator and not has_polynomial:
                        element = '单项式'
                    else:
                        element = '多项式'
        if element == '代数式':
            element = '单项式'
        return element

    def get_real_element(self, node):
        expr = simplify(self.expr_graph.node[node]['attr_dict']['expr'])
        if expr.is_Rational:
            # 有理数
            if expr.is_Integer:
                # 整数
                if expr.is_zero:
                    element = '0'
                else:
                    if expr.is_positive:
                        if expr.is_even:
                            element = '正偶数'
                        else:
                            element = '正奇数'
                    else:
                        if expr.is_even:
                            element = '负偶数'
                        else:
                            element = '负奇数'
            else:
                # 分数
                if expr.is_positive:
                    element = '正分数'
                else:
                    element = '负分数'
        else:
            # 无理数
            if expr.is_positive:
                element = '正无理数'
            else:
                element = '负无理数'
        return element

    def is_algebraic_expression(self, node):
        """
        代数式判别
            1,非关系式
            2,含有字母
            note:
                后期需要修复pi之类的常量
        """
        return (not self.is_relational_expression(node)) \
               and self.has_latin_alphabet(self.expr_graph.node[node]['attr_dict']['expr'])

    def is_relational_expression(self, node):
        """
        关系式判别
        """
        return self.expr_graph.node[node]['attr_dict']['expr'].is_Relational

    def is_real_expression(self, node):
        """
        实数判别
        """
        return not (self.is_relational_expression(node) or self.is_algebraic_expression(node))

    def has_latin_alphabet(self, expr_m):
        return len(re.findall(self.latin_alphabet_re, str(expr_m))) > 0

    def check_elements(self, source_element, target_element):
        if source_element == target_element:
            return True
        for element in self.element_relations[source_element]:
            if element == target_element:
                return True
        return False

    # def is_monomial_expression(self, node):
    #     """
    #     单项式判别:
    #       1,不再包含Add
    #       2,不再包含Sub
    #       2,包含字母
    #     """
    #     self
    #     return False
    #
    # def polynomial_expression(self, node):
    #     """
    #     多项式判别
    #       1,至少包含一个单项式
    #       2,最外层必须是Add或Sub
    #       Note:
    #           未化简的单项式乘以多项式、多项式乘以多项式，不属于多项式
    #     """
    #     self
    #     return False
    #
    # def is_fraction_expression(self, node):
    #     """
    #     分式判别:
    #       1,分子或分母必须是单项式
    #     """
    #     self
    #     return False
    #
    # def is_irrational_expression(self, node):
    #     """
    #     无理式判别
    #     """
    #     self
    #     return False
    #
    #
    # def is_inequality_expression(self, node):
    #     """
    #     不等式判别"
    #        1,忽略约束性质的不等式
    #        2,等是两边必须包含多元代数式
    #     """
    #     self
    #     return False
    #
    # def is_equation_expression(self, node):
    #     """
    #     等式判别
    #     """
    #     self
    #     return False

    # def is_equation(self, node):
    #     """
    #     方程判别
    #     """
    #     self
    #     return False
    #
    # def is_one_element_first_order_equation(self, node):
    #     """
    #     一元一次方程判别
    #     """
    #     self
    #     return False
    #
    # def is_one_element_second_order_equation(self, node):
    #     """
    #     一元二次方程判别
    #     """
    #     self
    #     return False
    #
    # def is_two_element_first_order_equation(self, node):
    #     """
    #     二元一次方程判别
    #     """
    #     self
    #     return False

    # def is_function(self):
    #     """
    #     函数判别
    #     """
    #     self
    #     return False
    #
    # def is_real(self, node):
    #     """
    #     实数判别
    #     """
    #     return False
    #
    # def is_rational(self, node):
    #     """
    #     有理数判别
    #     """
    #     return False
    #
    # def is_irrational(self, node):
    #     """
    #     无理数判别
    #     """
    #     return False
    #
    # def is_positive_rational(self, node):
    #     """
    #     正无理数判别
    #     """
    #     return False
    #
    # def is_negative_rational(self, node):
    #     """
    #     负无理数判别
    #     """
    #     return False
    #
    # def is_integer(self, node):
    #     """
    #     整数判别
    #     """
    #     return False
    #
    # def is_fraction(self, node):
    #     """
    #     分数判别
    #     """
    #     return False
    #
    # def is_positive_integer(self, node):
    #     """
    #     正整数判别
    #     """
    #     return False
    #
    # def is_negative_integer(self, node):
    #     """
    #     负整数判别
    #     """
    #     return False
    #
    # def is_zero(self, node):
    #     """
    #     0判别
    #     """
    #     return False
    #
    # def is_positive_odd(self, node):
    #     """
    #     正偶数判别
    #     """
    #     return False
    #
    # def is_positive_even(self, node):
    #     """
    #     正奇数判别
    #     """
    #     return False
    #
    # def is_negative_odd(self, node):
    #     """
    #     负偶数判别
    #     """
    #     return False
    #
    # def is_negative_even(self, node):
    #     """
    #     负奇数判别
    #     """
    #     return False
    #
    # def is_positive_fraction(self, node):
    #     """
    #     正分数判别
    #     """
    #     return False
    #
    # def is_negative_fraction(self, node):
    #     """
    #     负分数判别
    #     """
    #     return False
