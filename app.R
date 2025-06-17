library(shiny)
library(reticulate)
library(jsonlite)
library(dplyr)
library(purrr)
reticulate::use_python("/home/tom/Documents/biblio-bridge/venv/bin/python3.11", required = TRUE)
reticulate::py_config()

# Load Python function
source_python("openalex.py")

# Shiny UI
ui <- fluidPage(
  titlePanel("OpenAlex Metadata Fetch"),
  sidebarLayout(
    sidebarPanel(
      textInput("doi", "Enter DOI:", value = "10.1111/faf.12817"),
      textInput("email", "Enter Email (optional):", value = ""),
      numericInput("depth_level", "Reference Depth Level:", value = 0, min = 0, max = 5, step = 1),
      actionButton("fetch", "Fetch Metadata"),
      h4("Instructions"),
      p("Enter a DOI or OpenAlex ID and click 'Fetch Metadata'. The app will retrieve metadata for the input DOI or OpenAlex ID and, depending on set 'depth level' its referenced works, saving them as JSON files in the 'resulting_metadata' folder.")
    ),
    mainPanel(
      h3("Initial Metadata"),
      verbatimTextOutput("initial_output"),
      h3("Status"),
      verbatimTextOutput("status")
    )
  )
)

# Shiny Server
server <- function(input, output, session) {
  observeEvent(input$fetch, {
    # Create directories if they don't exist
    dir.create("metadata", showWarnings = FALSE)
    if (input$depth_level) {
      vec <- seq(0,input$depth_level,1)
      for (i in 1:length(vec)) {
        dir.create(paste("metadata/dl",i-1,sep = ""), showWarnings = FALSE)  
      }
    }
    
    # Fetch initial data using Python function
    initial_data <- fetch_openalex_data(input$doi, if (input$email != "") input$email else NULL)
    
    # Display initial data
    output$initial_output <- renderPrint({
      if ("error" %in% names(initial_data)) {
        initial_data$error
      } else {
        str(initial_data)
      }
    })
    
    # Save initial data
    if (!("error" %in% names(initial_data))) {
      doi_safe <- gsub("/", "_", input$doi)
      write_json(initial_data, paste0("metadata/initial_data_", doi_safe, ".json"), 
                 pretty = TRUE, auto_unbox = TRUE)
      output$status <- renderText({
        paste("Focal data saved to metadata/initial_data_", doi_safe, ".json")
      })
      
      # Recursive function to fetch references
      fetch_references_recursive <- function(ref_ids, current_depth, max_depth) {
        if (current_depth > max_depth || length(ref_ids) == 0) {
          return(NULL)
        }
        
        # Create directory for current depth
        dir.create(paste0("metadata/dl", current_depth-1), showWarnings = FALSE)
        next_level_refs <- list()
        
        # Fetch references with progress bar
        withProgress(message = paste("Fetching at depth level =", current_depth), value = 0, {
          for (i in seq_along(ref_ids)) {
            ref_data <- fetch_openalex_data(ref_ids[[i]], if (input$email != "") input$email else NULL)
            if (!("error" %in% names(ref_data))) {
              work_id <- sub(".*/", "", ref_data$id)
              write_json(ref_data, paste0("metadata/dl", current_depth-1, "/", work_id, ".json"), 
                         pretty = TRUE, auto_unbox = TRUE)
              next_level_refs <- c(next_level_refs, ref_data$referenced_works)
            }
            incProgress(1/length(ref_ids), detail = paste("Processing", i, "of", length(ref_ids)))
          }
        })
        
        # Update status
        output$status <- renderText({
          paste(output$status(), "\nDepth", current_depth, "references saved to metadata/dl", current_depth, "/")
        })
        
        # Fetch next level if not at max depth
        if (current_depth < max_depth) {
          fetch_references_recursive(unique(unlist(next_level_refs)), current_depth + 1, max_depth)
        }
      }
      
      # Fetch referenced works
      referenced_ids <- initial_data$referenced_works %||% list()
      if (length(referenced_ids) == 0) {
        output$status <- renderText({
          paste(output$status(), "\nNo referenced works found.")
        })
      } else {
        fetch_references_recursive(referenced_ids, 1, input$depth_level)
      }
    } else {
      output$status <- renderText({
        initial_data$error
      })
    }
  })
}

# Run the app
shinyApp(ui = ui, server = server)