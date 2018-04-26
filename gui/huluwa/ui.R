library(shiny)
library(shinythemes)

fluidPage(
  br(),
  br(),
  theme = shinytheme(theme = "paper"),
  # 输入框
  fluidRow(
    column(6,
           textInput('your_problem',
                     label = NULL,
                     value = 'x^2 + 4 = 8 + x',
                     width = '100%'),
           offset = 3,
           align="center"
    ),
    column(1,
           actionButton("solve_bt",
                        "GO",
                        width = '100%'))
  ),
  br(),
  fluidRow(
    column(4,
           radioButtons('text_type',
                        label = NULL,
                        choices = c('auto','latex','sympy','body'),
                        selected = 'latex',
                        inline = TRUE,
                        width = '100%'),
           offset = 4,
           align="center"
    )
  ),
  fluidRow(
    column(4,
           checkboxInput('parse_graph_display_ck',
                         label = 'diaplay parse graph',
                         value = TRUE,
                         width = '100%'),
           offset = 4,
           align="center"
    )

  ),
  br(),
  # 解析图
  fluidRow(
    column(11,
           visNetworkOutput("parse_graph",
                            width = "auto",
                            height = '400px'),
           offset = 1
    )
  ),
  br(),
  # 输出框,展示解题步骤
  fluidRow(
    column(6,
           uiOutput("my_answer_ui"),
           offset = 3
    )
  ),
  br(),
  # 习题库
  fluidRow(
    column(12,
           dataTableOutput('problems_db_dt'),
           offset = 0.2
    )
  ),
  br()
)