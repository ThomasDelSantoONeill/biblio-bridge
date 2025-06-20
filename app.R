library(shiny)
library(reticulate)
library(jsonlite)
library(dplyr)
library(purrr)

# Create or use a virtual environment
venv_dir <- "r-reticulate"
if (!virtualenv_exists(venv_dir)) {
  virtualenv_create(envname = venv_dir)
  virtualenv_install(envname = venv_dir, packages = c("requests", "numpy", "scikit-learn", "spacy", "aiohttp"), ignore_installed = TRUE)
}
use_virtualenv(venv_dir, required = TRUE)

reticulate::source_python("openalex.py")
reticulate::source_python("context_extract.py")

# Shiny UI
ui <- fluidPage(
  img(src="biblio-bridge.svg", height="32.5%", width="32.5%"),
  img(src="inst.svg", align = "right", height="50%", width="50%"),
  sidebarLayout(
    sidebarPanel(
      textInput("doi", "Enter DOI:", value = "10.1111/faf.12817"),
      textInput("email", "Enter Email (optional):", value = ""),
      numericInput("depth_level", "Reference Depth Level:", value = 0, min = 0, max = 5, step = 1),
      actionButton("fetch", "Fetch Metadata and Analyze"),
      h4("Instructions"),
      p("Enter a DOI or OpenAlex ID and click 'Fetch Metadata and Analyze'. The app will retrieve metadata for the input DOI or OpenAlex ID and its referenced works recursively, saving them as JSON files in the 'metadata' folder. It will then analyze the context and save results in the 'results' folder.")
    ),
    mainPanel(
      h3("Initial Metadata"),
      verbatimTextOutput("initial_output"),
      h3("Status"),
      verbatimTextOutput("status")
      # h3("Debug Info"),
      # verbatimTextOutput("debug")
    )
  ),
  img(src="caminos.svg", align = "right", height="60%", width="60%")
)

# Shiny Server
server <- function(input, output, session) {
  # Create reactive values for status and debug info
  status_log <- reactiveVal("")
  debug_log <- reactiveVal("")
  
  observeEvent(input$fetch, {
    # Reset status and debug
    status_log("")
    debug_log("")
    
    # Create directories if they don't exist
    dir.create("metadata", showWarnings = FALSE)
    if (input$depth_level > 0) {
      vec <- seq(0, input$depth_level - 1, 1)
      for (i in 1:length(vec)) {
        dir.create(paste("metadata/dl", i-1, sep = ""), showWarnings = FALSE)  
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
    
    # Save initial data and proceed
    if (!("error" %in% names(initial_data))) {
      doi_safe <- gsub("/", "_", input$doi)
      write_json(initial_data, paste0("metadata/initial_data_", doi_safe, ".json"), 
                 pretty = TRUE, auto_unbox = TRUE)
      
      # Recursive function to fetch references in batches
      fetch_references_recursive <- function(ref_ids, current_depth, max_depth) {
        if (current_depth > max_depth || length(ref_ids) == 0) {
          return(NULL)
        }
        
        # Create directory for current depth
        dir.create(paste0("metadata/dl", current_depth-1), showWarnings = FALSE)
        next_level_refs <- list()
        
        # Process references in batches of 5
        withProgress(message = paste("Fetching at depth level =", current_depth), value = 0, {
          for (i in seq(1, length(ref_ids), by = 5)) {
            batch <- ref_ids[i:min(i + 4, length(ref_ids))]
            # Fetch batch of up to 5 references
            ref_data_list <- fetch_openalex_data_batch(batch, if (input$email != "") input$email else NULL)
            
            # Process each result in the batch
            for (ref_data in ref_data_list) {
              if (!("error" %in% names(ref_data))) {
                work_id <- sub(".*/", "", ref_data$id)
                write_json(ref_data, paste0("metadata/dl", current_depth-1, "/", work_id, ".json"), 
                           pretty = TRUE, auto_unbox = TRUE)
                next_level_refs <- c(next_level_refs, ref_data$referenced_works)
                # Log saved file
                debug_log(paste(debug_log(), "\nSaved:", paste0("metadata/dl", current_depth-1, "/", work_id, ".json")))
              }
            }
            incProgress(min(5, length(ref_ids) - i + 1) / length(ref_ids), 
                        detail = paste("Processing", min(i + 4, length(ref_ids)), "of", length(ref_ids)))
          }
        })
        
        # Fetch next level if not at max depth
        if (current_depth < max_depth) {
          fetch_references_recursive(unique(unlist(next_level_refs)), current_depth + 1, max_depth)
        }
      }
      
      # Fetch referenced works and update status
      referenced_ids <- initial_data$referenced_works %||% list()
      debug_log(paste("Found", length(referenced_ids), "referenced works"))
      if (length(referenced_ids) == 0 || input$depth_level == 0) {
        # Set fetching status and run analysis
        status_log("Metadata fetched successfully")
        analysis_result <- process_json_files(doi_safe, input$depth_level)
        status_log(paste(status_log(), "\n", analysis_result$status))
        # Log analysis debug info
        if ("debug" %in% names(analysis_result)) {
          debug_log(paste(debug_log(), "\nAnalysis:", analysis_result$debug))
        }
      } else {
        # Run recursive fetching
        fetch_references_recursive(referenced_ids, 1, input$depth_level)
        # Set fetching status and run analysis
        status_log("Metadata fetched successfully")
        analysis_result <- process_json_files(doi_safe, input$depth_level)
        status_log(paste(status_log(), "\n", analysis_result$status))
        # Log analysis debug info
        # if ("debug" %in% names(analysis_result)) {
        #   debug_log(paste(debug_log(), "\nAnalysis:", analysis_result$debug))
        # }
      }
    } else {
      status_log(initial_data$error)
    }
    
    # Render outputs
    output$status <- renderText({
      status_log()
    })
    output$debug <- renderText({
      debug_log()
    })
  })
}

# Run the app
shinyApp(ui = ui, server = server)