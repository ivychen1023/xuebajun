
shinyServer(function(input, output, session){
  
  local_values <- reactiveValues(solutions_steps_dat = get_solutions_steps_dat('x^2 + 4 = 8 + x',
                                                                               'latex'))
  # local_values <- reactiveValues(solutions_steps_dat = get_solutions_steps_dat(input$your_problem,
  #                                                                              input$text_type))
  
  ######################################## 问题输入窗口 #######################################
  # 暂时不支持latex实时转成MathJax展示
  
  # 当选中习题时,输入框自动更新习题内容,此处也支持手动输入题干
  observeEvent(input$problems_db_dt_rows_selected,{
    updateTextInput(session,
                    inputId = 'your_problem',
                    value = problems_info_dat[input$problems_db_dt_rows_selected,][['题干']])
  })
  
  ######################################## 展示解析图 #######################################
  # 调python脚本,返回图谱数据
  # 支持多图展示
  output$parse_graph <- renderVisNetwork({
    if(input$parse_graph_display_ck){
      # print(local_values[['solutions_steps_dat']][['nodes_dat']])
      # print(local_values[['solutions_steps_dat']][['edges_dat']])
      visNetwork(
        nodes = local_values[['solutions_steps_dat']][['nodes_dat']],
        edges = local_values[['solutions_steps_dat']][['edges_dat']]
      ) %>%
        visEdges(arrows = list(to=list(enabled=TRUE))) %>%
        visHierarchicalLayout(sortMethod='directed')
    }
  })
  
  ######################################## 输出解题步骤 ####################################
  # 点击【GO】按钮,调python脚本解题并展示步骤
  observeEvent(input$solve_bt,{
    local_values[['solutions_steps_dat']] = get_solutions_steps_dat(input$your_problem,
                                                                    input$text_type)
    # print('~!!!!!!!!!!!!!!!!!!')
    # print(local_values[['solutions_steps_dat']][['steps_dat']])
  })
  
  # 单道题目展示
  solution_steps_display <- function(steps_dat){
    L <- vector("list", 0)
    if(nrow(steps_dat) > 0){
      L <- vector("list", 2*nrow(steps_dat))
      for(i in 1:nrow(steps_dat)){
        dat <- steps_dat[i,]
        L[[2*i - 1]] <- list(HTML(paste0(dat[['desc']], '<br>')))
        L[[2*i]] <- list(withMathJaxR(HTML(paste0(dat[['expr']], '<br>'))))
      }
    }
    return(L)
  }
  
  # 步骤展示,描述与结果不同颜色指示
  # 需要支持多到题目同时展示
  output$my_answer_ui <- renderUI({
    L <- vector("list", 0)
    dat <- local_values[['solutions_steps_dat']][['steps_dat']]
    # print('~~~~~~~~~~~~~~~~~~~~')
    # print(nrow(dat))
    if(nrow(dat) > 0){
      for(problem_id in unique(dat[['id']])){
        L <- append(L, solution_steps_display(dat[id==problem_id]))
        L <- append(L, list(HTML('<br>')))
      }
    }
    return(L)
  })
  
  ######################################## 习题库Table #####################################
  # 展示习题对应二级目标及习题题干
  output$problems_db_dt <- renderDataTable(
    if(input$text_type == 'body'){
      isolate({
        datatable(problems_info_dat,
                  selection = 'single',
                  rownames = FALSE)
      })
    }
  )
})