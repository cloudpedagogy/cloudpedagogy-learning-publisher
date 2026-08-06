group <- c("Vaccinated", "Unvaccinated")
cases <- c(5, 25)
population <- c(500, 500)
risk <- cases / population

barplot(
  risk,
  names.arg = group,
  col = c("steelblue", "tomato"),
  main = "Risk of Infection by Vaccination Status"
)
