import streamlit as st
import numpy as np
import pandas as pd
import altair as alt


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


############################################
# 2) Streamlit UI
############################################
st.title("📊 한국 은퇴 포트폴리오 시뮬레이터 🇰🇷")

with st.sidebar:
    st.header("🔧 입력 매개변수")

    # 🔹 나이 설정
    current_age = st.number_input(
        "현재 나이",
        min_value=18,
        max_value=90,
        value=30,
        step=1,
    )
    death_age = st.number_input(
        "기대 수명",
        min_value=current_age,
        max_value=100,
        value=90,
        step=1,
    )

    # 🔹 금융 설정
    current_savings = st.number_input(
        "현재 저축액 (KRW)",
        min_value=0,
        value=500_000_000,
        step=10_000_000,
    )

    # ✅ 연봉 & 종료 나이
    col1, col2 = st.columns([2, 1])
    with col1:
        annual_income_input = st.number_input(
            "연봉 (세전, KRW)",
            min_value=0,
            value=100_000_000,
            step=1_000_000,
        )
    with col2:
        income_end_age = st.number_input(
            "연봉 종료 나이",
            min_value=current_age,
            max_value=death_age,
            value=45,
            step=1,
        )

    # ✅ 기타 수입 & 종료 나이
    col3, col4 = st.columns([2, 1])
    with col3:
        other_income_input = st.number_input(
            "기타 수입 (연간, KRW)",
            min_value=0,
            value=120_000_000,
            step=1_000_000,
        )
    with col4:
        other_income_end_age = st.number_input(
            "종료 나이",
            min_value=current_age,
            max_value=death_age,
            value=70,
            step=1,
        )

    annual_expenses_input = st.number_input(
        "연간 지출 (KRW)",
        min_value=0,
        value=70_000_000,
        step=1_000_000,
    )

    # 🔹 투자 & 인플레이션
    expected_return = (
        st.slider(
            "기대 연간 수익률 (%)",
            0.0,
            10.0,
            6.0,
            step=0.1,
        )
        / 100
    )
    inflation_rate = (
        st.slider(
            "연간 인플레이션 (%)",
            0.0,
            10.0,
            2.0,
            step=0.1,
        )
        / 100
    )

    # 🔹 세금 설정 (양도소득세)
    capital_gains_tax_rate = (
        st.slider(
            "양도소득세율 (%)",
            0.0,
            30.0,
            22.0,
            step=0.1,
        )
        / 100
    )
    capital_gains_exemption = 2_500_000  # 예: 해외주식 공제 가정

# 🔹 FI 목표액 (25배 룰)
financial_independence_target = annual_expenses_input * 25

st.info("📌 간소화된 한국 은퇴 시뮬레이터입니다.")

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

portfolio = current_savings
cost_basis = current_savings  # 원금 추적을 위해, 초기에 '현금 저축액' 전부가 원금

depletion_age = None
fi_age = None

for idx, age in enumerate(years):
    # 매년 인플레이션 반영 (첫 해 제외)
    if idx > 0:
        annual_income = round(annual_income * (1 + inflation_rate))
        other_income = round(other_income * (1 + inflation_rate))
        annual_expenses = round(annual_expenses * (1 + inflation_rate))

    # 이번 해의 급여/기타소득 계산
    salary_income = annual_income if age < income_end_age else 0
    extra_income = other_income if age < other_income_end_age else 0
    total_income = salary_income + extra_income

    # 종합소득세
    income_tax = calculate_income_tax(total_income) if total_income > 0 else 0
    net_income = total_income - income_tax

    # -------------------------------
    # (A) 은퇴 전 (연봉이 존재)
    # -------------------------------
    if age < income_end_age:
        # 1) 포트폴리오 증가 (미실현 수익)
        investment_growth = round(portfolio * expected_return)
        portfolio += investment_growth

        # 2) 생활비 지출
        #    은퇴 전에는 '연봉+기타소득(세후)'로 지출 충당, 부족하면 포트폴리에서 꺼낸다고 가정
        cash_flow = net_income - annual_expenses

        # cash_flow가 +이면 남은 돈을 새로 투자 => cost_basis 증가
        # cash_flow가 -이면 부족분을 포트폴리에서 꺼냄 => 하지만 단순화: "미실현"으로 봐 세금 X
        if cash_flow >= 0:
            # 새로 투자 -> 원금(cost_basis)이 늘어남
            cost_basis += cash_flow
            portfolio += cash_flow
        else:
            # 부족분(-cash_flow)만큼 포트폴리에서 사용
            # 여기서 실제로 매도한 것으로 간주하면 세금을 계산해야 하지만,
            # 은퇴 전에는 "미실현/매도 안 함" 가정으로 간소화
            portfolio += cash_flow
            # cost_basis는 줄이거나/그대로 둘지 선택 가능
            # "현금 보유분"에서 충당한다고 가정하면 cost_basis 그대로 둘 수도 있음
            # 혹은 실제로 팔았다고 가정하면 cost_basis를 줄여야 함.
            # 여기서는 "미실현" 가정으로 cost_basis 변화 없음.
            pass

        # 은퇴 전에는 양도소득세 0, 인출도 0
        annual_withdrawal = 0
        capital_gains_tax_amount = 0

    # -------------------------------
    # (B) 은퇴 후 (연봉 종료 이후)
    # -------------------------------
    else:
        # 먼저 포트폴리오가 예상 수익률만큼 증가(미실현 상태)
        investment_growth = round(portfolio * expected_return)
        portfolio += investment_growth

        # 이제 실제로 "연간 지출액(annual_expenses)" 만큼 매도한다고 가정
        sell_amount = annual_expenses

        if sell_amount > portfolio:
            # 매도 금액이 포트폴리오를 초과하면 -> 고갈
            sell_amount = portfolio  # 가능한 만큼만 매도
            portfolio = 0
        else:
            portfolio -= sell_amount

        # (B-1) 매도 금액 중 원금/이익 비율
        total_unrealized_gains = portfolio + sell_amount - cost_basis
        # = (매도 전 잔액) - cost_basis
        # 여기서 매도 전 잔액 = portfolio + sell_amount

        # 만약 전체 포트폴리의 평가이익이 <= 0이면 양도차익 없음
        if total_unrealized_gains <= 0:
            # 전혀 이익이 없으므로 capital_gains = 0
            capital_gains = 0
            capital_gains_tax_amount = 0

            # 원금만 소진했다고 보고, cost_basis에서 sell_amount만큼 차감
            cost_basis -= sell_amount
            if cost_basis < 0:
                cost_basis = 0  # 음수가 되지 않도록 처리

        else:
            # 전체 포트폴리 중에서 매도액(sell_amount) 비율만큼 이익이 실현되었다고 봄
            # (매도 전) 포트폴리 총액 = (portfolio + sell_amount)
            portfolio_before_sell = portfolio + sell_amount

            # 매도 비율
            sell_ratio = sell_amount / portfolio_before_sell

            # 해당 비율만큼이 이익 부분에서 차지
            capital_gains = total_unrealized_gains * sell_ratio

            # 공제 적용
            taxable_gains = max(0, capital_gains - capital_gains_exemption)

            capital_gains_tax_amount = round(taxable_gains * capital_gains_tax_rate)

            # 매도액 중 '원금' 부분
            cost_basis_sold = sell_amount - capital_gains  # (매도액 - 이익 = 원금 부분)
            if cost_basis_sold < 0:
                cost_basis_sold = 0  # 혹시 음수면 0으로

            # cost_basis에서 해당 원금 부분만큼 차감
            cost_basis -= cost_basis_sold
            if cost_basis < 0:
                cost_basis = 0

        # 실제 인출액(= 생활비)
        annual_withdrawal = sell_amount

        # 매도 후 포트폴리오가 0 이하이면 고갈
        if portfolio <= 0 and depletion_age is None:
            depletion_age = age
            portfolio = 0

    # FI 달성 여부
    if fi_age is None and portfolio >= financial_independence_target:
        fi_age = age

    # 리스트 기록
    portfolio_values.append(portfolio)
    withdrawals.append(annual_withdrawal)
    taxes_paid.append(capital_gains_tax_amount)
    expenses_history.append(annual_expenses)
    income_values.append(salary_income)
    other_income_values.append(extra_income)
    income_taxes.append(income_tax)
    net_incomes.append(net_income)
    # 은퇴 후에서만 '실현' 이익을 표시할 수도 있으므로 구분
    # 여기서는 모든 해 investment_growth를 기록
    investment_growths.append(investment_growth)

# 결과 DataFrame
df = pd.DataFrame(
    {
        "나이": years,
        "연봉": income_values,
        "기타 수입": other_income_values,
        "소득세": income_taxes,
        "세후 소득": net_incomes,
        "연간 지출(인플레이션 반영)": expenses_history,
        "투자수익(연간)": investment_growths,
        "연간 인출액": withdrawals,
        "은퇴 후 납부세금(양도세)": taxes_paid,
        "포트폴리오 잔액": portfolio_values,
    }
)

# 결과 메시지
if fi_age is not None:
    st.success(f"🎉 {fi_age}세에 FI(Financial Independence)를 달성했습니다!")
if depletion_age is not None:
    st.error(f"⚠️ 포트폴리오가 {depletion_age}세에 고갈되었습니다.")

############################################
# 4) 시각화 및 결과 테이블
############################################
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

df_display = df.copy()

# Format all numeric columns except the first column
for col in df_display.columns[1:]:
    df_display[col] = df_display[col].apply(lambda x: f"{int(x):,} KRW")

# Set the first column as the index
df_display.set_index(df_display.columns[0], inplace=True)

# Display in Streamlit
st.dataframe(df_display)
