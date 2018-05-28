
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

if(Sys.info()[['sysname']] == 'Linux'){
    # use_python('/usr/bin/python3')
    Sys.setenv(RETICULATE_PYTHON = '/home/shiny/envs/venv/bin/python3')
    library(reticulate)
    setwd('/home/shiny/git/xuebajun/parse')
    # source_python('/home/shiny/git/xuebajun/parse/solvers.py')
}else{
  library(reticulate)
  use_python('/Library/Frameworks/Python.framework/Versions/3.6/bin/python3')
  setwd('/Users/wangguojie/git/xuebajun/parse')
  # source_python('/Users/wangguojie/git/xuebajun/parse/solvers.py')
}


# library(reticulate)
# use_python('/Library/Frameworks/Python.framework/Versions/3.6/bin/python3')
# setwd('/Users/wangguojie/git/xuebajun/parse')
# source_python('/Users/wangguojie/git/xuebajun/parse/solvers.py')

# 调python脚本,返回解题步骤
get_solutions_steps_dat <- function(problem_txt, txt_type='auto', debug_r=TRUE){
  if(Sys.info()[['sysname']] == 'Linux')
    source_python('/home/shiny/git/xuebajun/parse/solvers.py')
  else
    source_python('/Users/wangguojie/git/xuebajun/parse/solvers.py')
  steps_dat = NULL
  nodes_dat = NULL
  edges_dat = NULL
  log_info = NULL
  tryCatch({
    rst = huluwa_solvers(problem_txt, txt_type, debug_r)
    result_dat <- rst[1][[1]]
    graph_dat <- rst[2][[1]]
    log_info <- rst[3][[1]]
    # print(paste('log:', log_info))
    # print(paste('result_dat:', result_dat))
    log_info <- paste(log_info, collapse  = '<br>')
    edges_dat <- data.table(from=graph_dat[['from']],
                            to=graph_dat[['to']],
                            label=graph_dat[['edge_attr']])
    ids <- append(graph_dat[['from']], graph_dat[['to']])
    labels <- append(graph_dat[['from_attr']], graph_dat[['to_attr']])
    if(length(ids) > 0){
      for(i in 1:length(ids)){
        labels[i] <- paste(substr(ids[i], regexpr(' ', ids[i])[1] + 1, nchar(ids[i])), labels[i])
      }
    }
    nodes_dat <- data.table(id=ids,
                            label=labels)
    nodes_dat <- unique(nodes_dat, by="id")
    
    steps_dat <- data.table(id=result_dat[['id']],
                            desc=result_dat[['desc']],
                            expr=result_dat[['expr']],
                            theme=result_dat[['theme']],
                            end=result_dat[['end']])
  }, error = function(e) {})
  
  list(steps_dat = steps_dat,
       nodes_dat = nodes_dat,
       edges_dat = edges_dat,
       log_info = log_info)
}



# 获得日志信息
# get_log_info <- function(){
#   info <- ''
#   log_file <- 'logs/error.log'
#   if(file.exists(log_file))
#     info <- paste(readLines(log_file), sep = '\n')
#   info
# }



