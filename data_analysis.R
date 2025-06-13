library(rjson)
ini.doi <- fromJSON(file = "resulting_metadata/initial_data_10.1111_faf.12817.json")
dl0.files <- list.files(path = "resulting_metadata/dl0/")
dl1.files <- list.files(path = "resulting_metadata/dl1/")
dl0.vec <- c()
dl0.year <- c()
dl1.vec <- c()
dl1.year <- c()
for (i in 1:length(dl0.files)) {
  file.data <- fromJSON(file = paste("resulting_metadata/dl0/",dl0.files[i],sep = ""))
  dl0.vec[i] <- length(file.data$referenced_works)
  dl0.year[i] <- file.data$publication_year
}
for (i in 1:length(dl1.files)) {
  file.data <- fromJSON(file = paste("resulting_metadata/dl1/",dl1.files[i],sep = ""))
  dl1.vec[i] <- length(file.data$referenced_works)
  dl1.year[i] <- file.data$publication_year
}
sum(dl0.vec[-62])
sum(dl1.vec)
data <- data.frame(DL = as.factor(c("Focal", "DL0", "DL1", "DL2")),
                   No = c(1,89,3857, 108546))
library(ggplot2)
extrafont::loadfonts(device = "all")
library(latex2exp)
# Personalised theme
theme_tjdso <- theme(
  text = element_text(family = "Consolas", size = 20),
  panel.background = element_blank(),
  panel.border = element_rect(fill = FALSE),
  panel.grid.major = element_line(
    linetype = 3,
    colour = "grey",
    size = 0.25
  ),
  panel.grid.minor = element_line(
    linetype = 3,
    colour = "grey",
    size = 0.1
  ),
  strip.background = element_blank(),
  strip.text = element_text(size = 20),
  strip.placement = "outside",
  panel.spacing.x = unit(5, "mm"),
  axis.ticks.length = unit(-2, "mm"),
  axis.text.x.top = element_blank(),
  axis.text.y.right = element_blank(),
  axis.title.x.top = element_blank(),
  axis.title.y.right = element_blank(),
  axis.title = element_text(size = 18),
  axis.text.x.bottom = element_text(margin = margin(4, 0, 0, 0, "mm")),
  axis.text.y.left = element_text(margin = margin(0, 4, 0, 0, "mm"))
)
mod <- lm(log10(data$No)~as.integer(data$DL)[c(2,3,4,1)])
summary(mod)
ggplot(data = data, mapping = aes(x = 1:4, y = No)) +
  geom_hline(yintercept = 100000, colour = "darkred", linetype = 2, linewidth = 1) +
  geom_point(size = 8, fill = "steelblue", shape = 21, stroke = 1.25) +
  geom_smooth(method = "lm", se = FALSE, linetype = 1, colour = "black") +
  scale_y_log10(
    breaks = scales::trans_breaks("log10", function(x) 10^x),
    labels = scales::trans_format("log10", scales::math_format(10^.x))
  ) +
  scale_x_continuous(breaks=1:4,
                     labels=c("DL = 0", "DL = 1", "DL = 2", "DL = 3")) +
  labs(x = "Depth level",
       y = "Referenced works (No.)") +
  annotate(geom = "text", x = 1, y = 10^5.2, label = "Open Alex API rate limit",
           colour = "darkred", hjust = 0, family = "Consolas", size = 6) +
  annotate(geom = "curve", x = 2.5, y = 10^2.5, xend = 2.75, yend = 10^1.5,
             arrow = arrow(length = unit(0.3, "cm"), type = "closed"),
             color = "grey75",
             size = 1.2,
             curvature = 0.3
  ) +
  annotate(geom = "text", x = 2.8, y = 10^1.5, 
           label = TeX(r"(Increase of $\approx 1 \times 47^{DL}$)"),
           hjust = 0, family = "Consolas", size = 6) +
  theme_tjdso 

# Load required packages
library(jsonlite)
library(dplyr)
library(visNetwork)
library(stringr)

# Define paths
initial_json <- "resulting_metadata/initial_data_10.1111_faf.12817.json"
dl0_dir <- "resulting_metadata/dl0/"
dl1_dir <- "resulting_metadata/dl1/"

# Function to extract work ID from OpenAlex URL
extract_work_id <- function(id) {
  if (is.null(id) || is.na(id) || id == "") return(NA)
  str_extract(id, "W[0-9]+")
}

# Function to read a single JSON file and extract relevant fields
read_json_file <- function(file_path, depth) {
  tryCatch({
    json_data <- fromJSON(file_path, flatten = TRUE)
    ref_works <- if (is.null(json_data$referenced_works) || length(json_data$referenced_works) == 0) {
      character(0)
    } else {
      sapply(json_data$referenced_works, extract_work_id)
    }
    data.frame(
      id = extract_work_id(json_data$id),
      title = if (is.null(json_data$title)) "No title available" else json_data$title,
      publication_year = if (is.null(json_data$publication_year)) NA else json_data$publication_year,
      # cited_by_count = if (is.null(json_data$cited_by_count)) 0 else json_data$cited_count,
      referenced_works = I(list(ref_works)),
      depth = depth,
      stringsAsFactors = FALSE
    )
  }, error = function(e) {
    message("Error reading ", file_path, ": ", e$message)
    NULL
  })
}

# Read initial JSON (focal paper, depth 0)
initial_data <- read_json_file(initial_json, depth = 0)
if (is.null(initial_data)) stop("Failed to read initial JSON file.")

# Read all JSON files in dl0 (first-level references, depth 1)
dl0_files <- list.files(dl0_dir, pattern = "\\.json$", full.names = TRUE)
dl0_data <- lapply(dl0_files, function(f) read_json_file(f, depth = 1)) %>% bind_rows()

# Read all JSON files in dl1 (second-level references, depth 2)
dl1_files <- list.files(dl1_dir, pattern = "\\.json$", full.names = TRUE)
dl1_data <- lapply(dl1_files, function(f) read_json_file(f, depth = 2)) %>% bind_rows()

# Combine all data and remove duplicates by id
all_data <- bind_rows(initial_data, dl0_data, dl1_data) %>%
  filter(!is.na(id)) %>%
  distinct(id, .keep_all = TRUE)

# Create nodes data frame
nodes <- all_data %>%
  select(id, title, publication_year, depth) %>%
  mutate(
    label = paste0(id, "\n", substr(title, 1, 20), "..."),
    value = 0.1,  # Cap node size to avoid overcrowding
    title = paste0("<b>", title, "</b><br>Year: ", publication_year, "<br>Citations: "),
    group = paste0("DL", depth)
  )

# Create edges data frame
edges <- all_data %>%
  select(id, referenced_works) %>%
  tidyr::unnest(referenced_works) %>%
  filter(!is.na(referenced_works) & referenced_works != "") %>%
  rename(from = id, to = referenced_works) %>%
  filter(to %in% nodes$id) %>%
  mutate(
    color = case_when(
      from %in% nodes$id[nodes$depth == 0] ~ "rgba(255, 0, 0)",  # Red for DL0 with 10% opacity
      from %in% nodes$id[nodes$depth == 1] ~ "rgba(0, 0, 255, 0.1)",  # Blue for DL1 with 10% opacity
      from %in% nodes$id[nodes$depth == 2] ~ "rgba(0, 255, 0, 0.1)",  # Green for DL2 with 10% opacity
      TRUE ~ "rgba(128, 128, 128, 0.1)"  # Default gray with 10% opacity
    ),
    width = 0.5,
    arrows = "to"
  )

# Create improved circular visNetwork visualization
visNetwork(nodes, edges, width = "100%", height = "1200px") %>%
  visIgraphLayout() %>%
  visNodes(
    shape = "dot",
    scaling = list(min = 5, max = 20),  # Smaller nodes
    font = list(size = 12)
  ) %>%
  visEdges(
    arrows = "to",
    smooth = list(enabled = TRUE, type = "curvedCW", roundness = 0.2),  # Curved edges
    color = list(color = "gray", opacity = 0.1)  # Semi-transparent gray edges
  ) %>%
  visGroups(groupname = "DL0", color = "red") %>%
  visGroups(groupname = "DL1", color = "blue") %>%
  visGroups(groupname = "DL2", color = "green") %>%
  visOptions(
    highlightNearest = list(enabled = TRUE, degree = 1, hover = TRUE),  # Highlight edges on hover
    nodesIdSelection = TRUE
  ) %>%
  visInteraction(
    zoomView = TRUE,
    dragNodes = TRUE,
    hover = TRUE
  ) %>%
  visPhysics(
    stabilization = FALSE,
    barnesHut = list(gravitationalConstant = -5000, springLength = 200, springConstant = 0.01)
  )
