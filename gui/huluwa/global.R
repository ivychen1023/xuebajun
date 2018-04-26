
library(DT)
library(shiny)
library(data.table)
library(jsonlite)
library(mongolite)
library(shinythemes)
library(visNetwork)

# MathJax本地解析
withMathJaxR <- function(...)  {
  path <- "MathJax/MathJax.js?config=TeX-AMS-MML_HTMLorMML"
  tagList(tags$head(singleton(tags$script(src = path, type = "text/javascript"))),
          ..., tags$script(HTML("if (window.MathJax) MathJax.Hub.Queue([\"Typeset\", MathJax.Hub]);")),
          tags$script("type='text/x-mathjax-config',
                      MathJax.Hub.Config({
                      tex2jax: {inlineMath: [['$','$'], ['\\(','\\)']]}});
                      "))
}

# 获得习题库信息 
get_problem_db_infos <- function(){
  problems_info_conn <- mongo(collection="problems_info",
                              db = "knowledge_graph")
  problems_info_dat = problems_info_conn$find()
  data.table(二级目标=problems_info_dat[['goal_name']],
                 题干=problems_info_dat[['body']])
}

# 习题库Table
problems_info_dat <- get_problem_db_infos()

library(reticulate)
# use_python('/Library/Frameworks/Python.framework/Versions/3.6/bin/python3')
# setwd('/Users/wangguojie/git/xuebajun/parse')
# source_python('/Users/wangguojie/git/xuebajun/parse/solvers.py')

use_python('/usr/bin/python3')
setwd('/home/shiny/git/xuebajun/parse')
source_python('/home/shiny/git/xuebajun/parse/solvers.py')

# 调python脚本,返回解题步骤
get_solutions_steps_dat <- function(problem_txt, txt_type='auto'){
  rst = huluwa_solvers(problem_txt, txt_type)
  result_dat <- rst[1][[1]]
  graph_dat <- rst[2][[1]]
  edges_dat <- data.table(from=graph_dat[['from']],
                          to=graph_dat[['to']],
                          label=graph_dat[['edge_attr']])
  ids <- c(graph_dat[['from']], graph_dat[['to']])
  labels <- c(graph_dat[['from_attr']], graph_dat[['to_attr']])
  if(length(ids) > 0){
    for(i in 1:length(ids)){
      labels[i] <- paste(ids[i], labels[i])
    }
  }
  nodes_dat <- data.table(id=ids,
                          label=labels)
  nodes_dat <- unique(nodes_dat, by="id")
  # print('rst ;;;;;;;;')
  # print(rst)
  steps_dat <- data.table(id=result_dat[['id']],
                          desc=result_dat[['desc']],
                          expr=result_dat[['expr']])
  # print('steps_dat //////////')
  # print(steps_dat)
  
  list(steps_dat = data.table(id=result_dat[['id']],
                               desc=result_dat[['desc']],
                               expr=result_dat[['expr']]),
       nodes_dat = nodes_dat,
       edges_dat = edges_dat)
}


