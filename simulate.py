import streamlit as st
import numpy as np
import pandas as pd
import altair as alt


############################################
# 1) 종합소득세 계산 함수 (누진공제 방식)
############################################
def calculate_income_tax(income):
    """
    종합소득세율을 간단화하여 누진공제 표 기반으로 계산합니다.
    실제 계산과 다를 수 있으므로 참고용으로만 활용하세요.
    """
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


############################################
# 2) Streamlit UI
############################################

st.title("은퇴 포트폴리오 시뮬레이터 🇰🇷")

"""
이 시뮬레이터는 **개인투자자**를 위한 간단한 은퇴 자금 예측 도구입니다.
아래 입력 값을 조정하여, 연봉(세전), 저축액, 투자수익률, 세금 등을 고려한
장기 은퇴 계획을 시뮬레이션해 보세요.
"""

# 간단 안내문
st.info(
    "이 시뮬레이터는 **예시용**으로 작성된 것이며, 실제 세법/투자 환경과 다를 수 있습니다. "
    "금액과 세율 등은 각자의 상황에 맞게 조정하세요."
)

with st.sidebar:
    st.header("🔧 입력 매개변수")
    st.markdown("아래 입력란을 채워주세요. 결과는 오른쪽 메인 영역에 표시됩니다.")

    # 🔹 나이 설정
    current_age = st.number_input(
        "현재 나이",
        min_value=18,
        max_value=90,
        value=30,
        step=1,
        help="현재 본인의 실제 나이를 입력하세요. (18~90세 허용)",
    )
    death_age = st.number_input(
        "기대 수명(사망 나이)",
        min_value=current_age,
        max_value=110,
        value=90,
        step=1,
        help="얼마까지 살아갈 것으로 예상하는지 입력 (최대 110세).",
    )

    # 🔹 금융 설정
    current_savings = st.number_input(
        "현재 저축액 (KRW)",
        min_value=0,
        value=500_000_000,
        step=10_000_000,
        help="현재 보유 중인 총 저축액(투자원금, 현금, 예적금 등 포함).",
    )

    # ✅ 연봉 & 종료 나이
    col1, col2 = st.columns([2, 1])
    with col1:
        annual_income_input = st.number_input(
            "연봉 (세전, KRW)",
            min_value=0,
            value=100_000_000,
            step=1_000_000,
            help="연간 세전 연봉 총액. (0이면 소득 없음)",
        )
    with col2:
        income_end_age = st.number_input(
            "은퇴 나이",
            min_value=current_age,
            max_value=death_age,
            value=45,
            step=1,
            help="언제까지 이 연봉을 받을지. 이 나이 이후 연봉은 0이 됨.",
        )

    # ✅ 기타 수입 & 종료 나이
    col3, col4 = st.columns([2, 1])
    with col3:
        other_income_input = st.number_input(
            "기타 수입 (연간, KRW)",
            min_value=0,
            value=0,
            step=1_000_000,
            help="연봉 외 임대수익, 사업소득, 배당소득 등 연간 수입.",
        )
    with col4:
        other_income_end_age = st.number_input(
            "종료 나이",
            min_value=current_age,
            max_value=death_age,
            value=70,
            step=1,
            help="기타 수입이 몇 세까지 발생하는지 설정.",
        )

    annual_expenses_input = st.number_input(
        "연간 지출 (KRW)",
        min_value=0,
        value=70_000_000,
        step=1_000_000,
        help="연간 생활비. 은퇴 여부와 무관하게 기본 지출로 간주.",
    )

    # 🔹 투자 & 인플레이션
    st.markdown("#### 투자 및 물가상승률")
    expected_return = (
        st.slider(
            "기대 연간 수익률 (%)",
            0.0,
            10.0,
            6.0,
            step=0.1,
            help="투자 포트폴리오의 연평균 성장률(%) 가정.",
        )
        / 100
    )

    # 여기서는 단순하게 'inflation_rate' 하나만 사용 (연봉, 기타수입, 지출 모두 동일)
    inflation_rate = (
        st.slider(
            "연간 인플레이션 (%)",
            0.0,
            10.0,
            2.0,
            step=0.1,
            help="물가상승률 가정. 지출/연봉/기타 수입에 매년 적용.",
        )
        / 100
    )

    withdrawal_rate = (
        st.slider(
            "은퇴 후 인출률 (%)",
            1.0,
            10.0,
            4.0,
            step=0.1,
            help="은퇴 후 매년 포트폴리오에서 실제로 인출할 비율 (예: 4%룰).",
        )
        / 100
    )

    # 🔹 세금 설정 (양도소득세)
    st.markdown("#### 양도소득세(자본이득)에 대한 설정")
    capital_gains_tax_rate = (
        st.slider(
            "양도소득세율 (%)",
            0.0,
            30.0,
            22.0,
            step=0.1,
            help="실현된 투자이익에 매기는 세율 (예: 해외주식 22% 등)",
        )
        / 100
    )
    capital_gains_exemption = 2_500_000  # 예: 해외주식 공제 가정

# 🔹 FI 목표액 (25배 룰)
financial_independence_target = annual_expenses_input * 25

############################################
# 3) 시뮬레이션 로직
############################################
years = np.arange(current_age, death_age + 1)

# 결과 기록용 리스트
portfolio_values = []
withdrawals = []
taxes_paid = []
expenses_history = []
income_values = []
other_income_values = []
income_taxes = []
net_incomes = []
investment_growths = []

# 초기 값
annual_income = annual_income_input
other_income = other_income_input
annual_expenses = annual_expenses_input

# 현재 포트폴리오와 원금(cost basis)
portfolio = current_savings
cost_basis = current_savings  # 처음에는 '저축액 전부'가 원금

depletion_age = None
fi_age = None

# -----------------------------------
# 메인 시뮬레이션 반복 (나이= current_age ~ death_age)
# -----------------------------------
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

    # 종합소득세 (연봉+기타소득 합산)
    income_tax = calculate_income_tax(total_income) if total_income > 0 else 0
    net_income = total_income - income_tax

    # (A) 은퇴 전(연봉이 존재) vs (B) 은퇴 후(연봉 종료) 로직 분기
    if age < income_end_age:
        # --------------------------------------
        # (A) 은퇴 전: 아직 연봉이 있을 때
        # --------------------------------------
        # 1) 포트폴리오(미실현) 성장
        investment_growth = round(portfolio * expected_return)
        portfolio += investment_growth

        # 2) 생활비 지출(인플레이션 반영)
        cash_flow = net_income - annual_expenses
        if cash_flow >= 0:
            # 남은 돈(=저축액)은 새로 투자 -> cost_basis 증가
            cost_basis += cash_flow
            portfolio += cash_flow
        else:
            # 부족분은 포트폴리오에서 사용 (매도세는 단순화하여 생략)
            portfolio += cash_flow
            # 실제로는 cost_basis도 줄어들어야 맞지만, 여기서는 단순화
            # 은퇴 전에는 "미실현" 가정 -> 양도소득세 X

        # 은퇴 전엔 인출(=매도) 0, 양도소득세도 0
        annual_withdrawal = 0
        capital_gains_tax_amount = 0

        # 포트폴리오가 0 미만이면 고갈
        if portfolio < 0 and depletion_age is None:
            depletion_age = age
            portfolio = 0

    else:
        # --------------------------------------
        # (B) 은퇴 후: 연봉이 끊긴 이후
        # --------------------------------------
        # 1) 먼저 포트폴리오가 미실현 상태로 성장
        investment_growth = round(portfolio * expected_return)
        portfolio += investment_growth

        # 2) 설정한 인출률(%)만큼 실제 매도
        sell_amount = round(portfolio * withdrawal_rate)

        # 만약 포트폴리오가 부족하면 -> 고갈
        if sell_amount > portfolio:
            sell_amount = portfolio
            portfolio = 0
        else:
            portfolio -= sell_amount

        # 3) 매도액(sell_amount) 중 원금 vs. 이익 비중 계산
        portfolio_before_sell = portfolio + sell_amount  # 매도 전 잔액
        total_unrealized_gains = portfolio_before_sell - cost_basis

        if total_unrealized_gains <= 0:
            # 전체가 원금이므로 이익 없음 -> 양도소득세 0
            capital_gains = 0
            capital_gains_tax_amount = 0

            # cost_basis에서 매도액만큼 차감
            cost_basis -= sell_amount
            if cost_basis < 0:
                cost_basis = 0
        else:
            # 매도액 중 이익이 차지하는 비율
            sell_ratio = sell_amount / portfolio_before_sell
            capital_gains = total_unrealized_gains * sell_ratio

            # 양도소득세 계산 (공제 후 과세)
            taxable_gains = max(0, capital_gains - capital_gains_exemption)
            capital_gains_tax_amount = round(taxable_gains * capital_gains_tax_rate)

            # 매도액 중 원금 부분
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

    # FI 달성 여부 체크 (포트폴리오 >= 25 × 지출)
    if fi_age is None and portfolio >= financial_independence_target:
        fi_age = age

    # 결과 기록
    portfolio_values.append(portfolio)
    withdrawals.append(annual_withdrawal)
    taxes_paid.append(capital_gains_tax_amount)
    expenses_history.append(annual_expenses)
    income_values.append(salary_income)
    other_income_values.append(extra_income)
    income_taxes.append(income_tax)
    net_incomes.append(net_income)
    investment_growths.append(investment_growth)

# -----------------------------------
# 최종 결과 DataFrame 정리
# -----------------------------------
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
# 추가: 나이 자산 표시
###################################
# 시점의 자산
retire_portfolio = df.loc[df["나이"] == income_end_age, "포트폴리오 잔액"].values[0]
other_portfolio = df.loc[df["나이"] == other_income_end_age, "포트폴리오 잔액"].values[
    0
]
death_portfolio = df.loc[df["나이"] == death_age, "포트폴리오 잔액"].values[0]

# 데이터 구성
data = [
    [
        "FIRE 목표액",
        f"{annual_expenses_input:,.0f} KRW × 25",
        f"**{financial_independence_target:,.0f} KRW**",
    ],
    ["은퇴 나이", f"{income_end_age}세", f"{retire_portfolio:,.0f} KRW"],
    ["사망(기대 수명)", f"{death_age}세", f"{death_portfolio:,.0f} KRW"],
]

# 기타 수입 종료 나이 추가 (other_portfolio가 0이 아닐 때만)
if other_portfolio > 0:
    data.insert(
        2,
        [
            "기타 수입 종료 나이",
            f"{other_income_end_age}세",
            f"{other_portfolio:,.0f} KRW",
        ],
    )

# DataFrame 생성
df2 = pd.DataFrame(data, columns=["항목", "조건", "금액"]).set_index("항목")

# Streamlit 테이블 표시 (인덱스 없이)
st.table(df2.style.hide(axis="index"))

# 추가 설명 마크다운
st.markdown(
    f"""
- 은퇴 전에는 연봉+기타소득(세후)으로 생활비를 지출하고 남는 돈을 투자합니다.
- 은퇴 후에는 매년 포트폴리오 잔액의 {withdrawal_rate*100:.1f}%를 실제 매도(인출)합니다.
- 인출 분 중 원금 대비 이익 분을 계산해, 해외주식 양도소득세율({capital_gains_tax_rate*100:.1f}%)을 적용합니다.
- 연봉, 기타 수입, 연간 지출은 모두 매년 인플레이션({inflation_rate*100:.1f}%)을 적용해 상승한다고 가정했습니다.
- 소득(연봉+기타 수입)은 **종합소득세 함수**를 통해 세후 소득(Net Income)을 계산합니다.
"""
)

# -----------------------------------
# 결과 표시
# -----------------------------------
# FI 달성 여부
if fi_age is not None:
    st.success(f"🎉 축하합니다! {fi_age}세에 FIRE를 달성했습니다.")
else:
    st.info("아직 FIRE 목표액(지출 25배)에 도달하지 못했습니다.")

# 포트폴리오 고갈 여부
if depletion_age is not None:
    st.error(f"⚠️ 포트폴리오가 {depletion_age}세에 고갈되었습니다.")


# Altair 그래프
st.subheader("📊 포트폴리오 변동 그래프")

chart_data = pd.DataFrame({"나이": years, "포트폴리오 잔액": portfolio_values})
chart = (
    alt.Chart(chart_data)
    .mark_bar(color="steelblue")
    .encode(
        x=alt.X("나이:Q", title="나이"),
        y=alt.Y("포트폴리오 잔액:Q", title="포트폴리오 잔액 (KRW)"),
        tooltip=[
            alt.Tooltip("나이:Q"),
            alt.Tooltip("포트폴리오 잔액:Q", format=","),
        ],
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
