## Key Concept

Callout :: important

Vaccine effectiveness measures the reduction in disease risk among vaccinated individuals compared to unvaccinated individuals in real-world conditions.

END Callout

## Step-by-Step Calculation

Reveal

Label :: Show calculation

1.  Calculate risk in the vaccinated group: 5 / 500 = 0.01

2.  Calculate risk in the unvaccinated group: 25 / 500 = 0.05

3.  Relative Risk = 0.01 / 0.05 = 0.2

4.  VE = (1 − 0.2) × 100 = 80%

END Reveal

## Pause and Reflect

SelfCheck

Question :: Why might vaccine effectiveness differ between populations?

Answer :: Differences in exposure, population structure, healthcare access, and underlying health conditions can influence estimates.

END SelfCheck

## Youtube

YouTubeEmbed :: https://www.youtube.com/watch?v=yt3e8Ng0mf0

## Panopto

PanoptoEmbed :: https://lshtm.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id=d19ba573-9ad1-480b-95db-b3ed01014aab

## 

## R Code Demos  R Code and Output

R Code

R Mode :: static

Echo :: true

Output :: true

Alt :: Bar chart showing risk of infection for vaccinated and unvaccinated groups.

Caption :: Risk of Infection by Vaccination Status

group \<- c(\"Vaccinated\", \"Unvaccinated\")

cases \<- c(5, 25)

population \<- c(500, 500)

risk \<- cases / population

barplot(

risk,

names.arg = group,

col = c(\"steelblue\", \"tomato\"),

main = \"Risk of Infection by Vaccination Status\"

)

END R Code

## R Code Only

R Code

R Mode :: static

Echo :: true

Output :: false

group \<- c(\"Vaccinated\", \"Unvaccinated\")

cases \<- c(5, 25)

population \<- c(500, 500)

risk \<- cases / population

barplot(

risk,

names.arg = group,

col = c(\"steelblue\", \"tomato\"),

main = \"Risk of Infection by Vaccination Status\"

)

END R Code

## R Output Only

R Code

R Mode :: static

Echo :: false

Output :: true

Alt :: Bar chart comparing infection risk between vaccinated and unvaccinated groups.

Caption :: Risk of infection by vaccination status

group \<- c(\"Vaccinated\", \"Unvaccinated\")

cases \<- c(5, 25)

population \<- c(500, 500)

risk \<- cases / population

barplot(

risk,

names.arg = group,

col = c(\"steelblue\", \"tomato\"),

main = \"Risk of Infection by Vaccination Status\"

)

END R Code

## Interactive R Code

R Code

R Mode :: webr

Echo :: true

Output :: true

Alt :: Epidemic curve showing daily outbreak case counts.

Caption :: Simulated Epidemic Curve

days \<- 1:10

cases \<- c(2, 4, 7, 12, 18, 15, 11, 7, 4, 2)

barplot(

cases,

names.arg = days,

col = \"steelblue\",

xlab = \"Day\",

ylab = \"Number of Cases\",

main = \"Simulated Epidemic Curve\"

)

END R Code

## R Code Table example

R Code

R Mode :: webr

Echo :: true

Output :: true

data \<- data.frame(

Group = c(\"Vaccinated\", \"Unvaccinated\"),

Cases = c(5, 25),

Population = c(500, 500)

)

data\$Risk \<- data\$Cases / data\$Population

data

END R Code

## Interpreting the Results

Tabs

Tab :: Interpretation

An 80% vaccine effectiveness means vaccinated individuals have substantially lower risk compared to unvaccinated individuals.

END Tab

Tab :: Assumptions

The calculation assumes both groups are comparable and equally exposed.

END Tab

Tab :: Limitations

Confounding factors such as age, immunity, or healthcare access may influence results.

END Tab

END Tabs

## Epidemic Curve

Image :: resources/images/epidemic-curve.png

Alt :: Epidemic curve showing number of measles cases over time by vaccination status

Caption :: Epidemic curve comparing vaccinated and unvaccinated groups.

Width :: 70%

END Image

## Outbreak Report

File :: resources/pdf/outbreak-report.pdf

Display :: embed

Label :: View full outbreak investigation report

END File

## Download Dataset

File :: resources/data/outbreak-dataset.zip

Label :: Download full dataset

END File

## Quiz

Question :: Based on the outbreak data, what does a vaccine effectiveness of 80% mean in practice?

Option :: Vaccinated individuals have zero risk of infection

Option :: Vaccinated individuals have an 80% lower risk of infection than unvaccinated individuals

Option :: 80% of vaccinated individuals will not become infected

Option :: The vaccine prevents 80 cases in every outbreak regardless of context

Answer :: Vaccinated individuals have an 80% lower risk of infection than unvaccinated individuals

Explanation :: Vaccine effectiveness compares the risk of disease in vaccinated and unvaccinated groups under real-world conditions. An 80% VE means the vaccinated group experienced substantially lower risk, not that infection risk was eliminated entirely.

END Quiz

## 

## Key Takeaway

Callout :: tip

Vaccination significantly reduces the likelihood of infection and severe disease, even if it does not eliminate risk entirely.

END Callout

## Binomial Theorem equation

$$(x + a)^{n} = \sum_{k = 0}^{n}{\binom{n}{k}x^{k}a^{n - k}}$$

## Latex Equations Approach

**Display equation example**

\$\$\
P(X=x)=\\binom{n}{x}p\^x(1-p)\^{n-x}\
\$\$

## 
