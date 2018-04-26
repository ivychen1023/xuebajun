

def transposition(expr):
    # 加载需要的Package
    import sympy
    from sympy.parsing.sympy_parser import parse_expr
    expr_new = expr
    desc = None # desc == None 表示经过该函数,没有任何变化
    try:
        # 判断是否为关系式(等式、不等式)
        if expr.is_Relational:
            lh = expr.args[0]
            rh = expr.args[1]
            if rh.is_Add:
                if len(rh.args) == 0:
                    item = rh
                else:
                    item = rh.args[-1]
            else:
                item = rh
            # 相反数,也许可以优化，此处用字符串处理判断
            if expr.is_Equality:
                desc = "移项:等式两边同时"
            else:
                desc = "移项:不等式两边同时"
            if str(item).startswith('-'):
                item = parse_expr(str(item)[1:], evaluate=False)
                desc = ''.join([desc, "加上", str(item)])
            else:
                desc = ''.join([desc, "减去", str(item)])
                item = sympy.Mul(-1, item, evaluate=False)
            expr_new = expr.func(sympy.Add(lh, item, evaluate=False),
                                 sympy.Add(rh, item, evaluate=False))
    except:
        pass
    result = [{'expr': expr_new,
              'desc': desc}]
    return result


def check(expr):
    """
        关系式右边不为0
    """
    if expr.is_Relational and str(expr.args[1]) != '0':
        return True
    else:
        return False


# 换边
def switch_sides(expr):
    return [{'desc':'换边', 'expr': expr.func(expr.args[1], expr.args[0])}]


# 换边
def check(expr):
    """
        # 关系式且右边系数高于左边
    """
    from sympy import degree
    if expr.is_Relational and degree(expr.args[0]) < degree(expr.args[1]):
        return True
    else:
        return False



##################### 合并同类项
#合并同类项
def together(expr):
    # 加载需要的Package
    import sympy
    from sympy import Eq,separatevars
    expr_new = expr
    desc = None # desc == None 表示经过该函数,没有任何变化
        # 判断是否为关系式(等式、不等式)
    if expr.is_Relational:
        lh = expr.args[0]
        rh = expr.args[1]
        if expr.is_Equality:
            desc = "合并同类项:"
        else:
            desc = "合并同类项:"
        expr_new = expr.func(sympy.separatevars(lh),sympy.separatevars(rh))
        result = [{'desc': desc,'expr': expr_new}]
        return result


def together(expr):
    # 加载需要的Package
    import sympy
    from sympy import Eq,separatevars
    expr_new = expr
    desc = None # desc == None 表示经过该函数,没有任何变化
        # 判断是否为关系式(等式、不等式)
    if expr.is_Relational:
        lh = expr.args[0]
        rh = expr.args[1]
        if expr.is_Equality:
            desc = "合并同类项:"
        else:
            desc = "合并同类项:"
        expr_new = expr.func(sympy.simplify(lh),sympy.simplify(rh))
        result = [{'desc': desc,'expr': expr_new}]
        return result



def check(expr):
    """
        # 关系式
    """
    return expr.is_Relational



## 提取公因式
#提取公因式
def extractFactor(expr):
    # 加载需要的Package
    import sympy
    from sympy import Eq,factor
    expr_new = expr
    desc = None # desc == None 表示经过该函数,没有任何变化
        # 判断是否为关系式(等式、不等式)
    if expr.is_Relational:
        lh = expr.args[0]
        rh = 0
        if expr.is_Equality:
            desc = "合并同类项:"
        else:
            desc = "合并同类项:"
        expr_new = expr.func(factor(lh),0)
        result = [{'desc': desc,'expr': expr_new}]
        return result


def check(expr):
    return expr.is_Relational


########## 除法化简


#除法化简(只能化简整数，对于未知数用提取公因式)
def divideSimplify(expr):
    # 加载需要的Package
    import sympy
    from sympy import Eq,monic
    expr_new = expr
    desc = None # desc == None 表示经过该函数,没有任何变化
    # 判断是否为关系式(等式、不等式)
    if expr.is_Relational:
        lh = expr.args[0]
        rh = 0
        if expr.is_Equality:
            desc = "除法化简:"
        else:
            desc = "除法化简:"
        expr_new = expr.func(monic(lh),0)
    result = [{'desc': desc,'expr': expr_new}]
    return result


def check(expr):
    return expr.is_Relational




## 配方法
#配方法解一元二次方程 一定要是二次项系数、一次项系数都有且已化为标准形式
def solveCompletesquare(expr):
    from sympy import Poly,Eq,Add,solve
    from sympy.abc import x
    #expr = Eq(3*x+8*x**2+4,0)
    # desc = []
    result = []
    lh = expr.args[0]
    rh = expr.args[1]
    coeff_list = Poly(lh, x).all_coeffs()
    if coeff_list[2] ==0 and coeff_list[1] !=0:
        if coeff_list[0] == 1:
            lh_1 = lh
            rh_1 = rh
        else:
            lh_1 = lh/coeff_list[0]
            rh_1 = rh
        expr_1 = Eq(lh_1,rh_1)
        # desc.append('将二次项系数化为1:')
        # desc.append(expr_1)
        result.append({'desc': '将二次项系数化为1:', 'expr': expr_1})
        coeff_list_ = Poly(lh_1, x).all_coeffs()
        lh_1_ = Add(lh_1,(coeff_list_[1]/2)**2)
        rh_1_ = Add(rh_1,(coeff_list_[1]/2)**2)
        expr_1_ = Eq(lh_1_,rh_1_)
        # desc.append('等式左右两边同时加上一次项系数一半的平方')
        # desc.append(expr_1_)
        result.append({'desc': '等式左右两边同时加上一次项系数一半的平方', 'expr': expr_1_})
        expr_new = solve(expr_1_)
        # desc.append('配方法解一元二次方程:')
        # result = {'desc': desc,'配方法解一元二次方程得解:': expr_new}
        result.append({'desc': '配方法解一元二次方程', 'expr': expr_new})
        # for i in desc:
        #     print(i)
        return result
    if 0 not in coeff_list:
        lh_2 = Add(lh,-coeff_list[2])
        rh_2 = Add(rh,-coeff_list[2])
        expr_2 = Eq(lh_2,rh_2)
        # desc.append('将常数项移到等式的右边')
        # desc.append(expr_2)
        result.append({'desc': '将常数项移到等式的右边', 'expr': expr_2})
        coeff_list_new = Poly(lh_2, x).all_coeffs()
        if coeff_list_new[0] == 1:
            lh_3 = Add(lh_2,(coeff_list_new[1]/2)**2)
            rh_3 = Add(rh_2,(coeff_list_new[1]/2)**2)
            expr_3 = Eq(lh_3,rh_3)
            # desc.append('等式左右两边同时加上一次项系数一半的平方')
            # desc.append(expr_3)
            result.append({'desc': '等式左右两边同时加上一次项系数一半的平方', 'expr': expr_3})
            expr_new = solve(expr_3)
            # desc.append('配方法解一元二次方程:')
            # result = {'desc': desc,'配方法解一元二次方程得解:': expr_new}
            result.append({'desc': '配方法解一元二次方程', 'expr': expr_new})
        else:
            lh_4 = lh_2/coeff_list_new[0]
            rh_4 = rh_2/coeff_list_new[0]
            expr_4 = Eq(lh_4,rh_4)
            # desc.append('将二次项系数化为1')
            # desc.append(expr_4)
            result.append({'desc': '将二次项系数化为1', 'expr': expr_4})
            coeff_list_news = Poly(lh_4, x).all_coeffs()
            lh_5 = Add(lh_4,(coeff_list_news[1]/2)**2)
            rh_5 = Add(rh_4,(coeff_list_news[1]/2)**2)
            expr_5 = Eq(lh_5,rh_5)
            # desc.append('等式左右两边同时加上一次项系数一半的平方')
            # desc.append(expr_5)
            result.append({'desc': '等式左右两边同时加上一次项系数一半的平方', 'expr': expr_5})
            expr_new = solve(expr_5)
            result.append({'desc': '配方法解一元二次方程', 'expr': expr_new})
            # desc.append('配方法解一元二次方程:')
            # desc.append(expr_new)
            # for i in desc:
            #     print(i)
            # result = {'desc': desc,'配方法解一元二次方程得解:': expr_new}
    if len(result) == 0:
        result = [{'desc': None, 'expr': expr}]
    return result


