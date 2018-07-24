def Togerter_Ploy(expr):
    expr_new =  simplify(expr)
    result = [{'desc':"多项式合并同类项",'expr': expr_new,'step':'多项式合并同类项'}]
    return result