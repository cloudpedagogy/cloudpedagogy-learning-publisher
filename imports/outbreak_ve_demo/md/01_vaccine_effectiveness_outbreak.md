# Estimating Vaccine Effectiveness in an Outbreak

An outbreak of **measles**, a highly contagious viral disease, occurred in a semi-urban community with mixed vaccination coverage. Measles is one of the most transmissible infectious diseases, with a basic reproduction number (R₀) often estimated between 12 and 18.

Public health teams initiated an outbreak investigation to:

- identify confirmed and suspected cases

- determine vaccination status

- assess transmission patterns

- estimate the **real-world effectiveness of the vaccine**

For an overview of measles epidemiology, see:\
<https://www.who.int/news-room/fact-sheets/detail/measles>

## Understanding Vaccine Effectiveness

Vaccine effectiveness (VE) refers to how well a vaccine performs in real-world conditions, outside controlled clinical trials.

Unlike vaccine efficacy, effectiveness reflects:

- population diversity

- variation in exposure

- real-world healthcare access

- behavioural factors

👉 Learn more:\
<https://www.who.int/news-room/feature-stories/detail/vaccine-efficacy-effectiveness-and-protection>

## Why This Matters in Public Health

Estimating vaccine effectiveness is essential for:

- evaluating vaccination programmes

- identifying vulnerable populations

- informing outbreak response

- guiding policy decisions

For further reading:\
<https://pmc.ncbi.nlm.nih.gov/articles/PMC6734418/>

##  Key Concept

Callout :: important

Text :: Vaccine effectiveness measures the reduction in disease risk among vaccinated individuals compared to unvaccinated individuals in real-world conditions.

## Observed Data

The following table summarises the number of cases and non-cases among vaccinated and unvaccinated individuals during the outbreak.

  --------------------------------------------------------
  **Group**      **Cases (a, c)**   **Non-cases (b, d)**
  -------------- ------------------ ----------------------
  Vaccinated     4                  96

  Unvaccinated   20                 80
  --------------------------------------------------------

Table: Summary of outbreak cases by vaccination status

## Formula for Vaccine Effectiveness

Vaccine effectiveness is calculated as:

VE = (1 − Relative Risk) × 100

## Step-by-Step Calculation

Reveal\
Step 1 :: Calculate risk in the vaccinated group: 5 / 500 = 0.01\
Step 2 :: Calculate risk in the unvaccinated group: 25 / 500 = 0.05\
Step 3 :: Relative Risk = 0.01 / 0.05 = 0.2\
Step 4 :: VE = (1 − 0.2) × 100 = 80%

## Pause and Reflect

SelfCheck\
Question :: Why might vaccine effectiveness differ between populations?\
Answer :: Differences in exposure, population structure, healthcare access, and underlying health conditions can influence estimates.

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

Tabs\
Interpretation :: An 80% vaccine effectiveness means vaccinated individuals have substantially lower risk compared to unvaccinated individuals.\
Assumptions :: The calculation assumes both groups are comparable and equally exposed.\
Limitations :: Confounding factors such as age, immunity, or healthcare access may influence results.

## Epidemic Curve

Image :: resources/images/epidemic-curve.png\
Alt :: Epidemic curve showing number of measles cases over time by vaccination status\
Caption :: Epidemic curve comparing vaccinated and unvaccinated groups.\
Width :: 70%

## Outbreak Report

File :: resources/pdf/outbreak-report.pdf\
Display :: embed\
Label :: View full outbreak investigation report

## Download Dataset

File :: resources/data/outbreak-dataset.zip\
Label :: Download full dataset

## Quiz

Question :: Based on the outbreak data, what does a vaccine effectiveness of 80% mean in practice?

Option :: Vaccinated individuals have zero risk of infection

Option :: Vaccinated individuals have an 80% lower risk of infection than unvaccinated individuals

Option :: 80% of vaccinated individuals will not become infected

Option :: The vaccine prevents 80 cases in every outbreak regardless of context

Answer :: Vaccinated individuals have an 80% lower risk of infection than unvaccinated individuals

Explanation :: Vaccine effectiveness compares the risk of disease in vaccinated and unvaccinated groups under real-world conditions. An 80% VE means the vaccinated group experienced substantially lower risk, not that infection risk was eliminated entirely.

## 

## Key Takeaway

Callout :: tip\
Text :: Vaccination significantly reduces the likelihood of infection and severe disease, even if it does not eliminate risk entirely.

## Binomial Theorem equation

$$(x + a)^{n} = \sum_{k = 0}^{n}{\binom{n}{k}x^{k}a^{n - k}}$$

## Latex Equations Approach

**Display equation example**

\$\$\
P(X=x)=\\binom{n}{x}p\^x(1-p)\^{n-x}\
\$\$

## 

## Further Reading

WHO Measles Fact Sheet : <https://www.who.int/news-room/fact-sheets/detail/measles>\
Vaccine Effectiveness Overview : <https://www.who.int/news-room/feature-stories/detail/vaccine-efficacy-effectiveness-and-protection>\
Measles Vaccine Impact Study : <https://pmc.ncbi.nlm.nih.gov/articles/PMC6734418/>
