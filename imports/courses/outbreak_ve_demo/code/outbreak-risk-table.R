data <- data.frame(
  Group = c("Vaccinated", "Unvaccinated"),
  Cases = c(5, 25),
  Population = c(500, 500)
)

data$Risk <- data$Cases / data$Population

data
