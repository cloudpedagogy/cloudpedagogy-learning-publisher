# Estimating Vaccine Effectiveness in an Outbreak

An outbreak of **measles**, a highly contagious viral disease, occurred in a semi-urban community with mixed vaccination coverage. Measles is one of the most transmissible infectious diseases, with a basic reproduction number (R₀) often estimated between 12 and 18.

Public health teams initiated an outbreak investigation to:

1.  identify confirmed and suspected cases

2.  determine vaccination status

3.  assess transmission patterns

4.  estimate the **real-world effectiveness of the vaccine**

For an overview of measles epidemiology, see:\
<https://www.who.int/news-room/fact-sheets/detail/measles>

## Understanding Vaccine Effectiveness

Vaccine effectiveness (VE) refers to how well a vaccine performs in real-world conditions, outside controlled clinical trials.

Unlike vaccine efficacy, effectiveness reflects:

1.  population diversity

2.  variation in exposure

3.  real-world healthcare access

4.  behavioural factors

👉 Learn more:\
<https://www.who.int/news-room/feature-stories/detail/vaccine-efficacy-effectiveness-and-protection>

## Why This Matters in Public Health

Estimating vaccine effectiveness is essential for:

1.  evaluating vaccination programmes

2.  identifying vulnerable populations

3.  informing outbreak response

4.  guiding policy decisions

For further reading:\
<https://pmc.ncbi.nlm.nih.gov/articles/PMC6734418/>

##  Key Concept

Callout :: important

Vaccine effectiveness measures the reduction in disease risk among vaccinated individuals compared to unvaccinated individuals in real-world conditions.

END Callout

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

## Plotly Data visualistion

HTML Embed :: resources/html/steph1_plotly_distribution_demo_standalone.html

Title :: Distribution Explorer: Health-Related Measures

Height :: 750

END HTML Embed

## Youtube

YouTubeEmbed :: https://www.youtube.com/watch?v=yt3e8Ng0mf0

## 

## R Code Demos

## 

## R Code and Output

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

## Single Quiz

Quiz

Type :: single

Question :: Which R code correctly identifies patients with systolic blood pressure greater than or equal to 140 mmHg?

Option

Correct :: yes

The following code uses dplyr and the correct comparison operator:

R Example

R Mode :: static

Echo :: true

Output :: false

patients \|\>

dplyr::filter(systolic_bp \>= 140)

END R Example

Feedback :: Correct. The \>= operator retains patients with systolic blood pressure equal to or above 140 mmHg.

This includes a reading of exactly 140.

END Option

Option

Correct :: no

The following code selects values below 140:

R Example

R Mode :: static

Echo :: true

Output :: false

patients \|\>

dplyr::filter(systolic_bp \< 140)

END R Example

Feedback :: Not quite. The \< operator selects patients below the threshold rather than those at or above it.

END Option

Option

Correct :: no

The following code only selects readings above 140:

R Example

R Mode :: static

Echo :: true

Output :: false

patients \|\>

dplyr::filter(systolic_bp \> 140)

END R Example

Feedback :: Not quite. This excludes patients whose systolic blood pressure is exactly 140 mmHg.

END Option

Hint :: Look for the operator that means greater than or equal to.

Explanation :: The correct expression is systolic_bp \>= 140.

The \>= operator includes values greater than 140 and values equal to 140. This makes it appropriate when 140 mmHg is part of the threshold.

END Quiz

## Single Quiz

Quiz

Type :: single

Question :: Which expression correctly calculates vaccine effectiveness from a risk ratio?

Option

Correct :: yes

Vaccine effectiveness is calculated as:

\$\$

VE = (1-RR)\\times 100

\$\$

where \\(RR\\) is the risk ratio comparing vaccinated and unvaccinated groups.

Feedback :: Correct. Vaccine effectiveness represents the proportional reduction in risk associated with vaccination.

For example, if \\(RR=0.30\\), then \\(VE=70\\%\\).

END Option

Option

Correct :: no

Vaccine effectiveness is the risk ratio multiplied by 100:

\$\$

VE = RR\\times 100

\$\$

Feedback :: Not quite. This converts the risk ratio into a percentage but does not calculate the reduction in risk.

END Option

Option

Correct :: no

Vaccine effectiveness is calculated by subtracting the risk ratio from 100:

\$\$

VE = 100-RR

\$\$

Feedback :: Not quite. The risk ratio is normally expressed as a proportion and must first be subtracted from 1.

END Option

Hint :: Vaccine effectiveness measures the proportional reduction in risk among vaccinated people.

Explanation :: The correct formula is:

\$\$

VE = (1-RR)\\times 100

\$\$

If the risk ratio is \\(0.30\\), the calculation is:

\$\$

VE = (1-0.30)\\times 100 = 70\\%

\$\$

This indicates that vaccination is associated with a 70% reduction in risk.

END Quiz

## Single Quiz

Simple Single-Select Quiz

Quiz

Question :: Which expression correctly calculates vaccine effectiveness?

Option :: VE = (1 − RR) × 100

Option :: VE = RR × 100

Option :: VE = 100 − RR

Answer :: VE = (1 − RR) × 100

Hint :: Vaccine effectiveness measures the proportional reduction in risk.

Explanation :: The correct formula is VE = (1 − RR) × 100.

END Quiz

## Multiple Quiz

Quiz

Type :: multiple

Question :: Which R expressions would retain a patient whose systolic blood pressure is exactly 140 mmHg?

Option

Correct :: yes

R Example

R Mode :: static

Echo :: true

Output :: false

patients \|\>

dplyr::filter(systolic_bp \>= 140)

END R Example

Feedback :: Correct. The \>= operator includes 140.

END Option

Option

Correct :: yes

R Example

R Mode :: static

Echo :: true

Output :: false

patients \|\>

dplyr::filter(systolic_bp == 140)

END R Example

Feedback :: Correct. The == operator selects readings that are exactly 140.

END Option

Option

Correct :: no

R Example

R Mode :: static

Echo :: true

Output :: false

patients \|\>

dplyr::filter(systolic_bp \> 140)

END R Example

Feedback :: This excludes 140 because it only accepts values greater than 140.

END Option

Option

Correct :: no

R Example

R Mode :: static

Echo :: true

Output :: false

patients \|\>

dplyr::filter(systolic_bp \< 140)

END R Example

Feedback :: This selects readings below 140.

END Option

Hint :: More than one expression can include a reading of exactly 140.

Explanation :: Both \>= 140 and == 140 retain a value of exactly 140.

However, they have different meanings: \>= 140 also includes higher readings, while == 140 only includes readings equal to 140.

END Quiz

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

## Further Reading

WHO Measles Fact Sheet : <https://www.who.int/news-room/fact-sheets/detail/measles>\
Vaccine Effectiveness Overview : <https://www.who.int/news-room/feature-stories/detail/vaccine-efficacy-effectiveness-and-protection>\
Measles Vaccine Impact Study : <https://pmc.ncbi.nlm.nih.gov/articles/PMC6734418/>
