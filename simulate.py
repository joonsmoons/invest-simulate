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
def safe_get_int_param(key, default):
    try:
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
        help="당신의 현재 나이를 입력하세요. (만 나이)",
    )
    death_age = st.number_input(
        "기대 수명(사망 나이)",
        min_value=current_age,
        max_value=110,
        value=death_age_default,
        step=1,
        help="예상하는 사망 나이를 입력하세요. (기대 수명)",
    )
    current_savings = st.number_input(
        "현재 저축액 (KRW)",
        min_value=0,
        value=current_savings_default,
        step=10_000_000,
        help="현재 투자금 등 총 저축액을 입력하세요.",
    )

    # 연봉 & 종료 나이
    col1, col2 = st.columns([2, 1])
    with col1:
        annual_income_input = st.number_input(
            "연봉 (세전, KRW)",
            min_value=0,
            value=annual_income_default,
            step=1_000_000,
            help="세전 연봉(연간 총 수입)을 입력하세요.",
        )
    with col2:
        income_end_age = st.number_input(
            "은퇴 나이",
            min_value=current_age,
            max_value=death_age,
            value=income_end_age_default,
            step=1,
            help="몇 살까지 연봉 수익이 발생할 것인지 입력하세요.",
        )

    # 기타 수입 & 종료 나이
    col3, col4 = st.columns([2, 1])
    with col3:
        other_income_input = st.number_input(
            "기타 수입 (연간, KRW)",
            min_value=0,
            value=other_income_default,
            step=1_000_000,
            help="연봉 이외에 추가로 발생하는 연간 기타 수입을 입력하세요.",
        )
    with col4:
        other_income_end_age = st.number_input(
            "기타 수입 종료 나이",
            min_value=current_age,
            max_value=death_age,
            value=other_income_end_age_default,
            step=1,
            help="기타 수입이 언제까지 발생할 것인지 입력하세요.",
        )

    annual_expenses_input = st.number_input(
        "은퇴 전 연간 지출 (KRW)",
        min_value=0,
        value=annual_expenses_default,
        step=1_000_000,
        help="은퇴 전 1년 동안 예상되는 총 지출 금액 (매년 인플레이션 적용)",
    )

    # 투자 & 물가상승률
    st.markdown("#### 투자 및 물가상승률")
    slider_val_return = st.slider(
        "연간 기대 수익률 (%)",
        0.0,
        10.0,
        expected_return_slider_def,
        step=0.1,
        help="투자로 기대하는 연간 평균 수익률(%)을 입력하세요.",
    )
    expected_return = slider_val_return / 100.0

    slider_val_inflation = st.slider(
        "연간 인플레이션 (%)",
        0.0,
        10.0,
        inflation_rate_slider_def,
        step=0.1,
        help="연간 물가상승률(%)을 입력하세요. (은퇴 전 지출·소득에만 적용)",
    )
    inflation_rate = slider_val_inflation / 100.0

    # 세금 설정 (양도소득세)
    st.markdown("#### 양도소득세(자본이득) 설정")
    slider_val_cap_gains_tax = st.slider(
        "양도소득세율 (%)",
        0.0,
        50.0,
        cap_gains_tax_slider_def,
        step=0.1,
        help="투자 수익에 부과되는 양도소득세율(%)을 설정하세요. (해외주식 가정)",
    )
    capital_gains_tax_rate = slider_val_cap_gains_tax / 100.0

    # URL 파라미터 갱신
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
        "capital_gains_tax_rate": str(slider_val_cap_gains_tax),
    }
    st.query_params.from_dict(updated_params)

    st.write("---")
    st.write(
        """
        **이 링크를 복사**하여 다시 불러오거나 공유할 수 있습니다.
        """
    )


############################################
# 7) 시뮬레이션 로직
############################################
# - 은퇴 전(age < income_end_age): 인플레이션 반영 지출 사용
# - 은퇴 후(age >= income_end_age): 포트폴리오의 4%만 인출하여 전부 지출 (인플레이션 X)
############################################

years = np.arange(current_age, death_age + 1)
withdrawal_rate = 0.04  # 은퇴 후 인출률(고정 4%)
financial_independence_target = annual_expenses_input * 25

# 추적용 리스트
portfolio_values = []
withdrawals = []
taxes_paid = []
expenses_history = []
income_values = []
other_income_values = []
income_taxes = []
net_incomes = []
investment_growths = []

# 초기값 세팅
annual_income = annual_income_input  # 은퇴 전 기간 동안 매년 인플레이션 적용
other_income = (
    other_income_input  # 은퇴 전(또는 기타수입 종료 나이 전) 동안 인플레이션 적용
)
annual_expenses = annual_expenses_input  # 은퇴 전 지출(매년 인플레이션 반영)

portfolio = current_savings
cost_basis = current_savings

capital_gains_exemption = 2_500_000
depletion_age = None
fi_age = None

for idx, age in enumerate(years):

    # A) 매년의 '소득/지출'에 인플레이션을 반영하는 시점 (은퇴 전까지만)
    if idx > 0:
        # (1) 연봉/기타수입
        if age < income_end_age:  # 은퇴 전까지만 연봉/기타소득에 인플레 반영
            annual_income = round(annual_income * (1 + inflation_rate))
        if age < other_income_end_age:  # 기타수입도 종료 전까지만 인플레 반영
            other_income = round(other_income * (1 + inflation_rate))
        # (2) 은퇴 전 지출
        if age < income_end_age:
            annual_expenses = round(annual_expenses * (1 + inflation_rate))
        # 은퇴 이후에는 annual_expenses는 더이상 사용하지 않음 (4% 인출로 대체)

    # B) 해당 연도에 실제 발생하는 소득(연봉+기타수입)
    salary_income = annual_income if age < income_end_age else 0
    extra_income = other_income if age < other_income_end_age else 0
    total_income = salary_income + extra_income

    # C) 종합소득세 계산
    income_tax = calculate_income_tax(total_income) if total_income > 0 else 0
    net_income = total_income - income_tax

    # D) 투자수익 계산
    investment_growth = round(portfolio * expected_return)
    portfolio += investment_growth

    if age < income_end_age:
        # (1) 은퇴 전
        #     지출: annual_expenses (매년 인플레 반영)
        #     남거나 부족한 금액을 포트폴리오에 반영
        cash_flow = net_income - annual_expenses
        if cash_flow >= 0:
            # 남는 돈을 추가 투자 -> 원금(cost_basis)도 증가
            cost_basis += cash_flow
            portfolio += cash_flow
        else:
            # 지출이 더 많으면 모자란 만큼 포트폴리오에서 꺼내쓴다
            portfolio += cash_flow  # cash_flow는 음수
            # 포트폴리오에서 꺼낸 부분 중 원금 vs 이익 구분은 단순화

        annual_withdrawal = 0
        capital_gains_tax_amount = 0

    else:
        # (2) 은퇴 후
        #     은퇴 후 생활비 = "포트폴리오의 4%" (매년 다시 계산, 인플레 반영 X)
        annual_withdrawal = round(portfolio * withdrawal_rate)

        if annual_withdrawal > portfolio:
            # 포트폴리오가 모자라면 있는 만큼만 쓰고 0원
            annual_withdrawal = portfolio
            portfolio = 0
        else:
            portfolio -= annual_withdrawal

        # (2-a) 양도소득세 계산
        portfolio_before_sell = portfolio + annual_withdrawal
        total_unrealized_gains = portfolio_before_sell - cost_basis

        if total_unrealized_gains <= 0:
            capital_gains = 0
            capital_gains_tax_amount = 0
            cost_basis -= annual_withdrawal
            if cost_basis < 0:
                cost_basis = 0
        else:
            sell_ratio = annual_withdrawal / portfolio_before_sell
            capital_gains = total_unrealized_gains * sell_ratio

            # 양도소득 기본공제
            taxable_gains = max(0, capital_gains - capital_gains_exemption)
            capital_gains_tax_amount = round(taxable_gains * capital_gains_tax_rate)

            cost_basis_sold = annual_withdrawal - capital_gains
            if cost_basis_sold < 0:
                cost_basis_sold = 0
            cost_basis -= cost_basis_sold
            if cost_basis < 0:
                cost_basis = 0

    # E) 포트폴리오 고갈 여부
    if portfolio < 0 and depletion_age is None:
        depletion_age = age
        portfolio = 0

    # F) FIRE (재정적 독립) 달성 여부
    #    - 일반적으로 '연간 지출의 25배'를 넘으면 FIRE 달성으로 볼 수 있음
    if fi_age is None and portfolio >= financial_independence_target:
        fi_age = age

    # 로그 데이터 기록
    portfolio_values.append(portfolio)
    withdrawals.append(annual_withdrawal)
    taxes_paid.append(capital_gains_tax_amount)
    expenses_history.append(annual_expenses if age < income_end_age else 0)
    income_values.append(salary_income)
    other_income_values.append(extra_income)
    income_taxes.append(income_tax)
    net_incomes.append(net_income)
    investment_growths.append(investment_growth)

# 최종 DataFrame 구성
df = pd.DataFrame(
    {
        "나이": years,
        "포트폴리오 잔액": portfolio_values,
        "연봉(세전)": income_values,
        "기타 수입": other_income_values,
        "은퇴 전 세금(종합소득세)": income_taxes,
        "세후 소득": net_incomes,
        "은퇴 전 지출(인플레이션 적용)": expenses_history,
        "은퇴 후 인출금(=포트폴리오 4%)": withdrawals,
        "은퇴 후 세금(양도세)": taxes_paid,
        "연간 투자수익(미실현)": investment_growths,
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
        "FIRE 목표액 (연지출 25배)",
        f"{annual_expenses_default:,.0f} KRW × 25",
        f"**{(annual_expenses_default * 25):,.0f} KRW**",
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
- **은퇴 전**(나이 < {income_end_age}세)에는 매년 지출(인플레이션 적용)을 하고, 남는 소득을 저축합니다.
- **은퇴 후**(나이 ≥ {income_end_age}세)에는 더 이상 인플레이션 반영 지출을 사용하지 않고, 포트폴리오 잔액의 {withdrawal_rate*100:.0f}%만 매년 인출하여 생활비로 사용합니다.
- 연봉·기타 수입·지출은 은퇴 전 기간 동안 매년 인플레이션({inflation_rate*100:.1f}%)이 적용됩니다.
- 인출액 중 이익(원금 대비)에는 해외주식 양도소득세율({capital_gains_tax_rate*100:.1f}%)을 적용했습니다.
- 소득(연봉+기타 수입)은 **종합소득세 함수를 이용**해 세후 소득으로 반영됩니다.
"""
)

if fi_age is not None:
    st.success(f"🎉 축하합니다! {fi_age}세에 FIRE(재정적 독립)를 달성했습니다.")
else:
    st.info("아직 FIRE 목표액(연지출 25배)에 도달하지 못했습니다.")

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
- 의료비, 간병비 등 예외적 지출이 발생할 수 있으므로,
  은퇴 후 실제 생활비가 더 필요할 수 있다는 점을 유의하세요.
"""
)
