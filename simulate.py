import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
from urllib.parse import urlencode


############################################
# 1) 종합소득세 계산 함수 (누진공제 방식)
############################################
def calculate_income_tax(income):
    tax_brackets = [
        (12_000_000, 0.06, 0),
        (46_000_000, 0.15, 1_080_000),
        (88_000_000, 0.24, 5_220_000),
        (150_000_000, 0.35, 14_900_000),
        (300_000_000, 0.38, 19_400_000),
        (500_000_000, 0.40, 25_400_000),
        (1_000_000_000, 0.42, 35_400_000),
        (float("inf"), 0.45, 65_400_000),
    ]
    for limit, rate, deduction in tax_brackets:
        if income <= limit:
            return max(0, round(income * rate - deduction))
    return 0


######################################
# 2) Helper functions for query params
######################################
# st.query_params returns an object that behaves like a dictionary
# but also supports attribute notation (e.g. st.query_params.my_key).


def safe_get_int_param(key, default):
    try:
        # st.query_params[key] returns a string if it exists
        return int(st.query_params.get(key, default))
    except (ValueError, TypeError):
        return default


def safe_get_float_param(key, default):
    try:
        return float(st.query_params.get(key, default))
    except (ValueError, TypeError):
        return default


############################################
# 3) Streamlit UI
############################################
st.title("은퇴 포트폴리오 시뮬레이터 🇰🇷")
"""
이 시뮬레이터는 **개인투자자**를 위한 간단한 은퇴 자금 예측 도구입니다.
아래 입력 값을 조정하여, 연봉(세전), 저축액, 투자수익률, 세금 등을 고려한
장기 은퇴 계획을 시뮬레이션해 보세요.
"""

st.info(
    "이 시뮬레이터는 **예시용**으로 작성된 것이며, 실제 세법/투자 환경과 다를 수 있습니다. "
    "금액과 세율 등은 각자의 상황에 맞게 조정하세요."
)

############################
# 4) Load defaults from URL
############################
# Read from st.query_params (which are strings).
current_age_default = safe_get_int_param("current_age", 30)
death_age_default = safe_get_int_param("death_age", 90)
current_savings_default = safe_get_int_param("current_savings", 500_000_000)
annual_income_default = safe_get_int_param("annual_income_input", 100_000_000)
income_end_age_default = safe_get_int_param("income_end_age", 45)
other_income_default = safe_get_int_param("other_income_input", 0)
other_income_end_age_default = safe_get_int_param("other_income_end_age", 70)
annual_expenses_default = safe_get_int_param("annual_expenses_input", 70_000_000)

expected_return_slider_def = safe_get_float_param("expected_return", 6.0)
inflation_rate_slider_def = safe_get_float_param("inflation_rate", 2.0)
withdrawal_rate_slider_def = safe_get_float_param("withdrawal_rate", 4.0)
cap_gains_tax_slider_def = safe_get_float_param("capital_gains_tax_rate", 22.0)

###############################
# 5) Create the sidebar inputs
###############################
with st.sidebar:
    st.header("🔧 입력 매개변수")

    current_age = st.number_input(
        "현재 나이",
        min_value=18,
        max_value=90,
        value=current_age_default,
        step=1,
    )
    death_age = st.number_input(
        "기대 수명(사망 나이)",
        min_value=current_age,
        max_value=110,
        value=death_age_default,
        step=1,
    )
    current_savings = st.number_input(
        "현재 저축액 (KRW)",
        min_value=0,
        value=current_savings_default,
        step=10_000_000,
    )

    # 연봉 & 종료 나이
    col1, col2 = st.columns([2, 1])
    with col1:
        annual_income_input = st.number_input(
            "연봉 (세전, KRW)",
            min_value=0,
            value=annual_income_default,
            step=1_000_000,
        )
    with col2:
        income_end_age = st.number_input(
            "은퇴 나이",
            min_value=current_age,
            max_value=death_age,
            value=income_end_age_default,
            step=1,
        )

    # 기타 수입 & 종료 나이
    col3, col4 = st.columns([2, 1])
    with col3:
        other_income_input = st.number_input(
            "기타 수입 (연간, KRW)",
            min_value=0,
            value=other_income_default,
            step=1_000_000,
        )
    with col4:
        other_income_end_age = st.number_input(
            "종료 나이",
            min_value=current_age,
            max_value=death_age,
            value=other_income_end_age_default,
            step=1,
        )

    annual_expenses_input = st.number_input(
        "연간 지출 (KRW)",
        min_value=0,
        value=annual_expenses_default,
        step=1_000_000,
    )

    # 투자 & 물가상승률
    st.markdown("#### 투자 및 물가상승률")
    slider_val_return = st.slider(
        "기대 연간 수익률 (%)",
        0.0,
        10.0,
        expected_return_slider_def,
        step=0.1,
    )
    expected_return = slider_val_return / 100.0

    slider_val_inflation = st.slider(
        "연간 인플레이션 (%)",
        0.0,
        10.0,
        inflation_rate_slider_def,
        step=0.1,
    )
    inflation_rate = slider_val_inflation / 100.0

    withdrawal_slider_val = st.slider(
        "은퇴 후 인출률 (%)",
        1.0,
        10.0,
        withdrawal_rate_slider_def,
        step=0.1,
    )
    withdrawal_rate = withdrawal_slider_val / 100.0

    # 세금 설정 (양도소득세)
    st.markdown("#### 양도소득세(자본이득) 설정")
    slider_val_cap_gains_tax = st.slider(
        "양도소득세율 (%)",
        0.0,
        30.0,
        cap_gains_tax_slider_def,
        step=0.1,
    )
    capital_gains_tax_rate = slider_val_cap_gains_tax / 100.0

    # (해외주식 공제 예시)
    capital_gains_exemption = 2_500_000

    # ----------------------------------------------------
    # 6) Update st.query_params via from_dict in one go
    # ----------------------------------------------------
    # All values must be strings or lists of strings for repeated keys.
    # Here, we have single values only.
    updated_params = {
        "current_age": str(current_age),
        "death_age": str(death_age),
        "current_savings": str(current_savings),
        "annual_income_input": str(annual_income_input),
        "income_end_age": str(income_end_age),
        "other_income_input": str(other_income_input),
        "other_income_end_age": str(other_income_end_age),
        "annual_expenses_input": str(annual_expenses_input),
        "expected_return": str(slider_val_return),
        "inflation_rate": str(slider_val_inflation),
        "withdrawal_rate": str(withdrawal_slider_val),
        "capital_gains_tax_rate": str(slider_val_cap_gains_tax),
    }
    st.query_params.from_dict(updated_params)

    # 현재 설정된 파라미터를 공유할 수 있는 링크 제공
    st.write("---")
    st.write(
        "**이 링크를 공유하세요** 입력값을 다시 불러오거나 다른 사람에게 보낼 수 있습니다:"
    )
    params_dict = st.query_params.to_dict()
    query_string = urlencode(params_dict, doseq=True)
    share_link = "?" + query_string

    if st.button("공유 링크 복사"):
        copy_script = f"""
        <script>
        navigator.clipboard.writeText('{share_link}');
        </script>
        """
        st.markdown(copy_script, unsafe_allow_html=True)
        st.success("링크가 클립보드에 복사되었습니다!")


############################################
# 7) 시뮬레이션 로직 (unchanged)
############################################
financial_independence_target = annual_expenses_input * 25
years = np.arange(current_age, death_age + 1)

portfolio_values = []
withdrawals = []
taxes_paid = []
expenses_history = []
income_values = []
other_income_values = []
income_taxes = []
net_incomes = []
investment_growths = []

annual_income = annual_income_input
other_income = other_income_input
annual_expenses = annual_expenses_input

portfolio = current_savings
cost_basis = current_savings

depletion_age = None
fi_age = None

for idx, age in enumerate(years):
    # 매년 인플레이션 반영 (첫 해 제외)
    if idx > 0:
        annual_income = round(annual_income * (1 + inflation_rate))
        other_income = round(other_income * (1 + inflation_rate))
        annual_expenses = round(annual_expenses * (1 + inflation_rate))

    # 이번 해의 급여 + 기타소득
    salary_income = annual_income if age < income_end_age else 0
    extra_income = other_income if age < other_income_end_age else 0
    total_income = salary_income + extra_income

    # 종합소득세 (연봉+기타수입 합산)
    income_tax = calculate_income_tax(total_income) if total_income > 0 else 0
    net_income = total_income - income_tax

    if age < income_end_age:
        # (A) 은퇴 전
        investment_growth = round(portfolio * expected_return)
        portfolio += investment_growth

        cash_flow = net_income - annual_expenses
        if cash_flow >= 0:
            cost_basis += cash_flow
            portfolio += cash_flow
        else:
            portfolio += cash_flow

        annual_withdrawal = 0
        capital_gains_tax_amount = 0

        if portfolio < 0 and depletion_age is None:
            depletion_age = age
            portfolio = 0
    else:
        # (B) 은퇴 후
        investment_growth = round(portfolio * expected_return)
        portfolio += investment_growth

        sell_amount = round(portfolio * withdrawal_rate)
        if sell_amount > portfolio:
            sell_amount = portfolio
            portfolio = 0
        else:
            portfolio -= sell_amount

        portfolio_before_sell = portfolio + sell_amount
        total_unrealized_gains = portfolio_before_sell - cost_basis

        if total_unrealized_gains <= 0:
            capital_gains = 0
            capital_gains_tax_amount = 0
            cost_basis -= sell_amount
            if cost_basis < 0:
                cost_basis = 0
        else:
            sell_ratio = sell_amount / portfolio_before_sell
            capital_gains = total_unrealized_gains * sell_ratio

            taxable_gains = max(0, capital_gains - capital_gains_exemption)
            capital_gains_tax_amount = round(taxable_gains * capital_gains_tax_rate)

            cost_basis_sold = sell_amount - capital_gains
            if cost_basis_sold < 0:
                cost_basis_sold = 0
            cost_basis -= cost_basis_sold
            if cost_basis < 0:
                cost_basis = 0

        annual_withdrawal = sell_amount

        if portfolio <= 0 and depletion_age is None:
            depletion_age = age
            portfolio = 0

    if fi_age is None and portfolio >= financial_independence_target:
        fi_age = age

    portfolio_values.append(portfolio)
    withdrawals.append(annual_withdrawal)
    taxes_paid.append(capital_gains_tax_amount)
    expenses_history.append(annual_expenses)
    income_values.append(salary_income)
    other_income_values.append(extra_income)
    income_taxes.append(income_tax)
    net_incomes.append(net_income)
    investment_growths.append(investment_growth)

df = pd.DataFrame(
    {
        "나이": years,
        "포트폴리오 잔액": portfolio_values,
        "연봉": income_values,
        "기타 수입": other_income_values,
        "소득세": income_taxes,
        "세후 소득": net_incomes,
        "연간 지출(인플레이션 반영)": expenses_history,
        "투자수익(연간)": investment_growths,
        "연간 인출액(포트폴리오 %)": withdrawals,
        "은퇴 후 납부세금(양도세)": taxes_paid,
    }
)

###################################
# 8) 결과 요약
###################################
retire_portfolio = df.loc[df["나이"] == income_end_age, "포트폴리오 잔액"].values[0]
other_portfolio = df.loc[df["나이"] == other_income_end_age, "포트폴리오 잔액"].values[
    0
]
death_portfolio = df.loc[df["나이"] == death_age, "포트폴리오 잔액"].values[0]

data = [
    [
        "FIRE 목표액",
        f"{annual_expenses_input:,.0f} KRW × 25",
        f"**{(annual_expenses_input * 25):,.0f} KRW**",
    ],
    ["은퇴 나이", f"{income_end_age}세", f"{retire_portfolio:,.0f} KRW"],
    ["사망(기대 수명)", f"{death_age}세", f"{death_portfolio:,.0f} KRW"],
]
if other_portfolio > 0:
    data.insert(
        2,
        [
            "기타 수입 종료 나이",
            f"{other_income_end_age}세",
            f"{other_portfolio:,.0f} KRW",
        ],
    )

df2 = pd.DataFrame(data, columns=["항목", "조건", "금액"]).set_index("항목")
st.table(df2.style.hide(axis="index"))

st.markdown(
    f"""
- 은퇴 전에는 연봉+기타소득(세후)으로 생활비를 지출하고 남는 돈을 투자합니다.
- 은퇴 후에는 매년 포트폴리오 잔액의 {withdrawal_rate*100:.1f}%를 실제 매도(인출)합니다.
- 인출 분 중 원금 대비 이익 분을 계산해, 해외주식 양도소득세율({capital_gains_tax_rate*100:.1f}%)을 적용합니다.
- 연봉, 기타 수입, 연간 지출은 모두 매년 인플레이션({inflation_rate*100:.1f}%)을 적용해 상승한다고 가정했습니다.
- 소득(연봉+기타 수입)은 **종합소득세 함수**를 통해 세후 소득(Net Income)을 계산합니다.
"""
)

if fi_age is not None:
    st.success(f"🎉 축하합니다! {fi_age}세에 FIRE를 달성했습니다.")
else:
    st.info("아직 FIRE 목표액(지출 25배)에 도달하지 못했습니다.")

if depletion_age is not None:
    st.error(f"⚠️ 포트폴리오가 {depletion_age}세에 고갈되었습니다.")

st.subheader("📊 포트폴리오 변동 그래프")
chart_data = pd.DataFrame({"나이": years, "포트폴리오 잔액": portfolio_values})
chart = (
    alt.Chart(chart_data)
    .mark_bar(color="steelblue")
    .encode(
        x=alt.X("나이:Q", title="나이"),
        y=alt.Y("포트폴리오 잔액:Q", title="포트폴리오 잔액 (KRW)"),
        tooltip=[alt.Tooltip("나이:Q"), alt.Tooltip("포트폴리오 잔액:Q", format=",")],
    )
    .properties(width=700, height=400)
)
st.altair_chart(chart, use_container_width=True)

st.subheader("📋 시뮬레이션 결과 데이터")
"""
아래 테이블에서 매년(나이별) 포트폴리오 변화, 소득, 세금, 인출 내역 등을 확인할 수 있습니다.
계산 과정에서 정수 반올림이 이뤄집니다.
"""
df_display = df.copy().set_index("나이")
for col in df_display.columns[1:]:
    df_display[col] = df_display[col].apply(lambda x: f"{int(x):,} KRW")
st.dataframe(df_display)

st.markdown(
    """
---
**주의사항:**
- 실제 투자상품(해외주식, 국내주식, 부동산 등)에 따라 세율, 공제, 과세 방법이 달라질 수 있습니다.
- 본 시뮬레이터는 여러 가정을 단순화하여 작성된 예시 코드이므로,
  개인별 정확한 재무 설계를 위해서는 전문가와의 상담이 필요합니다.
- 은퇴 이후에도 의료비나 기타 지출이 증가할 수 있으며, 세부 시나리오에 따라 다르게 모델링해야 합니다.
"""
)
