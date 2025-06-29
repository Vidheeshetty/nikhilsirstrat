
# 📈 Swing Range Expansion Strategy (Interday)

## 🧠 Strategy Logic
This strategy captures momentum breakouts after a **narrow range day**, anticipating volatility expansion the next day.

---

## ✅ Entry Criteria

**Long Entry:**
- Today's candle is a **NR7 day** (narrowest range in last 7 days).
- Next day: Break above today’s **high** triggers long.

**Short Entry:**
- NR7 condition met.
- Next day: Break below today’s **low** triggers short.

---

## 🚪 Exit Criteria

- **Target:** 1.5x range of NR7 day.
- **Stop Loss:** 0.75x range of NR7 day.
- Or **exit after 3 bars**, whichever is earlier.

---

## 🔢 Sample Calculation

If on 2023-06-01:
- High = 18659.00
- Low = 18550.00
- Range = 109

Then on 2023-06-02:
- Entry long = above 18659.00
- Target = 18659.00 + 1.5 × 109 = **18822.50**
- SL = 18659.00 - 0.75 × 109 = **18577.25**

---

## 📊 Why This Works

- NR7 days often precede breakouts.
- Uses **volatility contraction → expansion** logic.
- Doesn't rely on indicators, just price action.

---

## 🛠️ Backtesting Notes

- Can be implemented in Python with pandas for custom backtests.
- Or integrated into **NautilusTrader** using bar data without bid/ask prices.
- Requires just `HIGH`, `LOW`, `CLOSE` series and date indexing.

