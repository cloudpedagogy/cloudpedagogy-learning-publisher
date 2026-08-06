days <- 1:10

cases <- c(2, 4, 7, 12, 18, 15, 11, 7, 4, 2)

barplot(
  cases,
  names.arg = days,
  col = "steelblue",
  xlab = "Day",
  ylab = "Number of Cases",
  main = "Simulated Epidemic Curve"
)
