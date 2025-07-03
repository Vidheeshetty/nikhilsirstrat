"""Concrete implementations of signal generators.

This module provides implementations of common signal generation strategies
using the pluggable signal architecture.
"""

import pandas as pd
from typing import Dict, Any, List

from .base import BaseSignalGenerator, SignalConfig, TradingSignal, SignalType
from utils.indicators.base import IndicatorValue


class SMAFractalSignalGenerator(BaseSignalGenerator):
    """Signal generator combining SMA crossover with fractal confirmation.
    
    This implementation matches the exact logic from the original SMA Fractal Scalper V1
    strategy, ensuring identical signal generation behavior.
    """
    
    def __init__(self, config: SignalConfig):
        super().__init__(config)
        
        # State tracking for crossover detection (like V1)
        self._prev_trend: str = None
        self._closes = []  # Track closes for SMA calculation
        self._highs = []   # Track highs for fractal calculation  
        self._lows = []    # Track lows for fractal calculation
        
    def _validate_parameters(self) -> None:
        """Validate SMA Fractal signal parameters."""
        required_params = ["sma_short_period", "sma_long_period", "fractal_window"]
        for param in required_params:
            if param not in self.parameters:
                raise ValueError(f"SMAFractalSignalGenerator requires '{param}' parameter")
        
        # Get parameters
        self.sma_short_period = self.parameters["sma_short_period"]
        self.sma_long_period = self.parameters["sma_long_period"] 
        self.fractal_window = self.parameters["fractal_window"]
        self.use_sma = self.parameters.get("use_sma", True)
        self.use_fractals = self.parameters.get("use_fractals", True)
        
        # Validate parameters
        if self.sma_short_period >= self.sma_long_period:
            raise ValueError("Short SMA period must be < long SMA period")
        if self.fractal_window < 1 or self.fractal_window % 2 == 0:
            raise ValueError("fractal_window must be odd and >=1")
            
        # Set required indicators
        self.required_indicators = ["sma_short", "sma_long", "fractal"]
    
    def _get_latest_fractals(self, fractal_indicator: IndicatorValue) -> tuple:
        """Get latest fractal high and low values."""
        if not fractal_indicator or not fractal_indicator.values:
            return None, None
            
        fractal_high = fractal_indicator.values.get("fractal_high")
        fractal_low = fractal_indicator.values.get("fractal_low")
        
        # Convert 0 values to None (no fractal)
        fractal_high = fractal_high if fractal_high and fractal_high > 0 else None
        fractal_low = fractal_low if fractal_low and fractal_low > 0 else None
        
        return fractal_high, fractal_low
    
    def _generate_signal(
        self, 
        indicator_values: Dict[str, IndicatorValue],
        market_data: Dict[str, float]
    ) -> TradingSignal:
        """Generate signal based on SMA crossover and fractal confirmation.
        
        This matches the exact logic from the original V1 strategy.
        """
        
        timestamp = market_data.get('timestamp', pd.Timestamp.now())
        current_price = market_data.get('close', 0.0)
        bar_high = market_data.get('high', current_price)
        bar_low = market_data.get('low', current_price)
        bar_open = market_data.get('open', current_price)
        
        # Get indicator values
        sma_short = indicator_values["sma_short"].get_main_value()
        sma_long = indicator_values["sma_long"].get_main_value()
        
        reasons = []
        confidence = 0.0
        signal_type = SignalType.NO_SIGNAL
        entry_price = current_price
        stop_price = None
        
        # -------------------- Determine *trend* -----------------------
        trend = None
        if self.use_sma:
            # Need SMA values first
            if sma_short is None or sma_long is None:
                return TradingSignal(
                    signal_type=SignalType.NO_SIGNAL,
                    timestamp=timestamp,
                    confidence=0.0,
                    price=current_price,
                    reasons=["Insufficient SMA data"],
                    metadata={}
                )
                
            if sma_short > sma_long:
                trend = "LONG"
            elif sma_short < sma_long:
                trend = "SHORT"
            else:
                return TradingSignal(
                    signal_type=SignalType.NO_SIGNAL,
                    timestamp=timestamp,
                    confidence=0.0,
                    price=current_price,
                    reasons=["SMA values equal - no trend"],
                    metadata={}
                )

            # Fire only on crossover (trend change) - CRITICAL V1 LOGIC
            if trend == self._prev_trend:
                return TradingSignal(
                    signal_type=SignalType.NO_SIGNAL,
                    timestamp=timestamp,
                    confidence=0.0,
                    price=current_price,
                    reasons=[f"Trend unchanged ({trend}); waiting for opposite crossover"],
                    metadata={"trend": trend, "prev_trend": self._prev_trend}
                )
            self._prev_trend = trend

        # -------------------- Pure fractal mode ----------------------
        fractal_high, fractal_low = self._get_latest_fractals(indicator_values["fractal"])

        if not self.use_sma:
            # Direction decided solely by breakout
            if fractal_high is not None and (
                bar_high > fractal_high or 
                (self.fractal_window == 1 and bar_high == fractal_high)
            ):
                trend = "LONG"
                signal_type = SignalType.LONG
                entry_price = max(bar_open, fractal_high)
                stop_price = fractal_low if fractal_low is not None else bar_low
                confidence = 0.8
                reasons.append(f"Fractal high breakout: {bar_high:.2f} > {fractal_high:.2f}")
                
            elif fractal_low is not None and (
                bar_low < fractal_low or 
                (self.fractal_window == 1 and bar_low == fractal_low)
            ):
                trend = "SHORT"
                signal_type = SignalType.SHORT
                entry_price = min(bar_open, fractal_low)
                stop_price = fractal_high if fractal_high is not None else bar_high
                confidence = 0.8
                reasons.append(f"Fractal low breakout: {bar_low:.2f} < {fractal_low:.2f}")
            else:
                return TradingSignal(
                    signal_type=SignalType.NO_SIGNAL,
                    timestamp=timestamp,
                    confidence=0.0,
                    price=current_price,
                    reasons=["No fractal breakout detected"],
                    metadata={}
                )

        # If SMA used but fractals disabled, enter immediately --------
        if self.use_sma and not self.use_fractals:
            signal_type = SignalType.LONG if trend == "LONG" else SignalType.SHORT
            entry_price = current_price
            stop_price = bar_low if trend == "LONG" else bar_high
            confidence = 0.7
            reasons.append(f"SMA crossover: {trend} trend confirmed")
            reasons.append(f"SMA values: {sma_short:.2f} {'>' if trend == 'LONG' else '<'} {sma_long:.2f}")

        # ----------------------- SMA + fractal entry ---------
        elif self.use_sma and self.use_fractals:
            if (
                trend == "LONG"
                and fractal_high is not None
                and (
                    bar_high > fractal_high or 
                    (self.fractal_window == 1 and bar_high == fractal_high)
                )
            ):
                signal_type = SignalType.LONG
                entry_price = max(bar_open, fractal_high)
                stop_price = fractal_low if fractal_low is not None else bar_low
                confidence = 0.9
                reasons.append(f"SMA bullish crossover: {sma_short:.2f} > {sma_long:.2f}")
                reasons.append(f"Fractal high breakout: {bar_high:.2f} > {fractal_high:.2f}")
                
            elif (
                trend == "SHORT"
                and fractal_low is not None
                and (
                    bar_low < fractal_low or 
                    (self.fractal_window == 1 and bar_low == fractal_low)
                )
            ):
                signal_type = SignalType.SHORT
                entry_price = min(bar_open, fractal_low)
                stop_price = fractal_high if fractal_high is not None else bar_high
                confidence = 0.9
                reasons.append(f"SMA bearish crossover: {sma_short:.2f} < {sma_long:.2f}")
                reasons.append(f"Fractal low breakout: {bar_low:.2f} < {fractal_low:.2f}")
            else:
                # SMA crossover detected but waiting for fractal breakout
                gap_msg = ""
                if trend == "LONG" and fractal_high is not None:
                    gap_val = fractal_high - bar_high
                    if gap_val > 0.00001:
                        gap_msg = f"LONG gap: need {gap_val:.2f} higher (bar.high={bar_high:.2f} vs fractal={fractal_high:.2f})"
                    else:
                        gap_msg = f"LONG gap: price reached fractal level ({bar_high:.2f}) but must exceed it"
                elif trend == "SHORT" and fractal_low is not None:
                    gap_val = fractal_low - bar_low
                    if gap_val > 0.00001:
                        gap_msg = f"SHORT gap: need {gap_val:.2f} lower (bar.low={bar_low:.2f} vs fractal={fractal_low:.2f})"
                    else:
                        gap_msg = f"SHORT gap: price reached fractal level ({bar_low:.2f}) but must break below"
                
                return TradingSignal(
                    signal_type=SignalType.NO_SIGNAL,
                    timestamp=timestamp,
                    confidence=0.0,
                    price=current_price,
                    reasons=[f"SMA {trend} crossover detected", gap_msg or "Waiting for fractal breakout"],
                    metadata={"trend": trend, "fractal_high": fractal_high, "fractal_low": fractal_low}
                )

        # Return the signal
        return TradingSignal(
            signal_type=signal_type,
            timestamp=timestamp,
            confidence=confidence,
            price=entry_price,
            reasons=reasons,
            metadata={
                "trend": trend,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "sma_short": sma_short,
                "sma_long": sma_long,
                "fractal_high": fractal_high,
                "fractal_low": fractal_low,
                "direction": trend
            }
        )


class RSIBollingerSignalGenerator(BaseSignalGenerator):
    """Signal generator combining RSI with Bollinger Bands."""
    
    def _validate_parameters(self) -> None:
        """Validate RSI Bollinger signal parameters."""
        # Set default parameters
        if "rsi_oversold" not in self.parameters:
            self.parameters["rsi_oversold"] = 30
        if "rsi_overbought" not in self.parameters:
            self.parameters["rsi_overbought"] = 70
        
        # Validate indicator requirements
        required_indicators = ["rsi", "bollinger_bands"]
        self.required_indicators = required_indicators
    
    def _generate_signal(
        self, 
        indicator_values: Dict[str, IndicatorValue],
        market_data: Dict[str, float]
    ) -> TradingSignal:
        """Generate signal based on RSI and Bollinger Bands."""
        
        timestamp = market_data.get('timestamp', pd.Timestamp.now())
        current_price = market_data.get('close', 0.0)
        
        # Get indicator values
        rsi = indicator_values["rsi"].get_main_value()
        bb_upper = indicator_values["bollinger_bands"].values.get("upper_band", 0)
        bb_middle = indicator_values["bollinger_bands"].values.get("middle_band", 0)
        bb_lower = indicator_values["bollinger_bands"].values.get("lower_band", 0)
        
        reasons = []
        confidence = 0.0
        signal_type = SignalType.NO_SIGNAL
        
        rsi_oversold = self.parameters["rsi_oversold"]
        rsi_overbought = self.parameters["rsi_overbought"]
        
        # Check for oversold conditions
        if rsi < rsi_oversold and current_price <= bb_lower:
            signal_type = SignalType.LONG
            confidence = 0.9
            reasons.append(f"RSI oversold: {rsi:.1f} < {rsi_oversold}")
            reasons.append(f"Price at/below lower BB: {current_price:.2f} <= {bb_lower:.2f}")
            
        # Check for overbought conditions
        elif rsi > rsi_overbought and current_price >= bb_upper:
            signal_type = SignalType.SHORT
            confidence = 0.9
            reasons.append(f"RSI overbought: {rsi:.1f} > {rsi_overbought}")
            reasons.append(f"Price at/above upper BB: {current_price:.2f} >= {bb_upper:.2f}")
            
        # Check for moderate signals
        elif rsi < rsi_oversold:
            signal_type = SignalType.HOLD
            confidence = 0.6
            reasons.append(f"RSI oversold: {rsi:.1f} < {rsi_oversold}")
            reasons.append("Waiting for Bollinger Band confirmation")
            
        elif rsi > rsi_overbought:
            signal_type = SignalType.HOLD
            confidence = 0.6
            reasons.append(f"RSI overbought: {rsi:.1f} > {rsi_overbought}")
            reasons.append("Waiting for Bollinger Band confirmation")
            
        else:
            signal_type = SignalType.HOLD
            confidence = 0.3
            reasons.append(f"RSI neutral: {rsi:.1f}")
            reasons.append(f"Price within BB range: {bb_lower:.2f} - {bb_upper:.2f}")
        
        return TradingSignal(
            signal_type=signal_type,
            timestamp=timestamp,
            confidence=confidence,
            price=current_price,
            reasons=reasons,
            metadata={
                "rsi": rsi,
                "bb_upper": bb_upper,
                "bb_middle": bb_middle,
                "bb_lower": bb_lower,
                "bb_position": "above" if current_price > bb_upper else "below" if current_price < bb_lower else "within"
            }
        )


class TrendFollowingSignalGenerator(BaseSignalGenerator):
    """Signal generator for trend following using multiple indicators."""
    
    def _validate_parameters(self) -> None:
        """Validate trend following signal parameters."""
        # Set default parameters
        if "min_indicators_agree" not in self.parameters:
            self.parameters["min_indicators_agree"] = 2
        
        # Validate indicator requirements
        required_indicators = ["sma_short", "sma_long", "ema"]
        self.required_indicators = required_indicators
    
    def _generate_signal(
        self, 
        indicator_values: Dict[str, IndicatorValue],
        market_data: Dict[str, float]
    ) -> TradingSignal:
        """Generate trend following signal."""
        
        timestamp = market_data.get('timestamp', pd.Timestamp.now())
        current_price = market_data.get('close', 0.0)
        
        # Get indicator values
        sma_short = indicator_values["sma_short"].get_main_value()
        sma_long = indicator_values["sma_long"].get_main_value()
        ema = indicator_values["ema"].get_main_value()
        
        reasons = []
        confidence = 0.0
        signal_type = SignalType.NO_SIGNAL
        
        # Count bullish/bearish indicators
        bullish_count = 0
        bearish_count = 0
        
        # SMA trend
        if sma_short > sma_long:
            bullish_count += 1
            reasons.append(f"SMA bullish: {sma_short:.2f} > {sma_long:.2f}")
        elif sma_short < sma_long:
            bearish_count += 1
            reasons.append(f"SMA bearish: {sma_short:.2f} < {sma_long:.2f}")
        
        # Price vs EMA
        if current_price > ema:
            bullish_count += 1
            reasons.append(f"Price above EMA: {current_price:.2f} > {ema:.2f}")
        elif current_price < ema:
            bearish_count += 1
            reasons.append(f"Price below EMA: {current_price:.2f} < {ema:.2f}")
        
        # Price vs SMA long
        if current_price > sma_long:
            bullish_count += 1
            reasons.append(f"Price above SMA long: {current_price:.2f} > {sma_long:.2f}")
        elif current_price < sma_long:
            bearish_count += 1
            reasons.append(f"Price below SMA long: {current_price:.2f} < {sma_long:.2f}")
        
        min_agree = self.parameters["min_indicators_agree"]
        
        # Generate signal based on agreement
        if bullish_count >= min_agree:
            signal_type = SignalType.LONG
            confidence = min(0.9, 0.5 + (bullish_count * 0.15))
        elif bearish_count >= min_agree:
            signal_type = SignalType.SHORT
            confidence = min(0.9, 0.5 + (bearish_count * 0.15))
        else:
            signal_type = SignalType.HOLD
            confidence = 0.3
            reasons.append(f"Insufficient agreement: {bullish_count} bullish, {bearish_count} bearish")
        
        return TradingSignal(
            signal_type=signal_type,
            timestamp=timestamp,
            confidence=confidence,
            price=current_price,
            reasons=reasons,
            metadata={
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
                "min_required": min_agree,
                "sma_short": sma_short,
                "sma_long": sma_long,
                "ema": ema
            }
        )


class MeanReversionSignalGenerator(BaseSignalGenerator):
    """Signal generator for mean reversion strategies."""
    
    def _validate_parameters(self) -> None:
        """Validate mean reversion signal parameters."""
        # Set default parameters
        if "bb_std_threshold" not in self.parameters:
            self.parameters["bb_std_threshold"] = 2.0
        if "rsi_extreme_threshold" not in self.parameters:
            self.parameters["rsi_extreme_threshold"] = 20  # More extreme than normal
        
        # Validate indicator requirements
        required_indicators = ["bollinger_bands", "rsi"]
        self.required_indicators = required_indicators
    
    def _generate_signal(
        self, 
        indicator_values: Dict[str, IndicatorValue],
        market_data: Dict[str, float]
    ) -> TradingSignal:
        """Generate mean reversion signal."""
        
        timestamp = market_data.get('timestamp', pd.Timestamp.now())
        current_price = market_data.get('close', 0.0)
        
        # Get indicator values
        rsi = indicator_values["rsi"].get_main_value()
        bb_upper = indicator_values["bollinger_bands"].values.get("upper_band", 0)
        bb_middle = indicator_values["bollinger_bands"].values.get("middle_band", 0)
        bb_lower = indicator_values["bollinger_bands"].values.get("lower_band", 0)
        
        reasons = []
        confidence = 0.0
        signal_type = SignalType.NO_SIGNAL
        
        rsi_extreme = self.parameters["rsi_extreme_threshold"]
        
        # Calculate how far price is from BB middle
        bb_width = bb_upper - bb_lower
        if bb_width > 0:
            price_bb_position = (current_price - bb_middle) / (bb_width / 2)  # -1 to +1
        else:
            price_bb_position = 0
        
        # Check for extreme oversold conditions (mean reversion buy)
        if (current_price < bb_lower and 
            rsi < rsi_extreme and 
            abs(price_bb_position) > 1.0):
            
            signal_type = SignalType.LONG
            confidence = 0.85
            reasons.append(f"Extreme oversold: RSI {rsi:.1f} < {rsi_extreme}")
            reasons.append(f"Price below lower BB: {current_price:.2f} < {bb_lower:.2f}")
            reasons.append(f"BB position: {price_bb_position:.2f}")
            
        # Check for extreme overbought conditions (mean reversion sell)
        elif (current_price > bb_upper and 
              rsi > (100 - rsi_extreme) and 
              abs(price_bb_position) > 1.0):
            
            signal_type = SignalType.SHORT
            confidence = 0.85
            reasons.append(f"Extreme overbought: RSI {rsi:.1f} > {100 - rsi_extreme}")
            reasons.append(f"Price above upper BB: {current_price:.2f} > {bb_upper:.2f}")
            reasons.append(f"BB position: {price_bb_position:.2f}")
            
        # Check for moderate mean reversion opportunities
        elif current_price < bb_lower and rsi < 30:
            signal_type = SignalType.HOLD
            confidence = 0.6
            reasons.append(f"Moderate oversold: RSI {rsi:.1f} < 30")
            reasons.append(f"Price at lower BB: {current_price:.2f} <= {bb_lower:.2f}")
            
        elif current_price > bb_upper and rsi > 70:
            signal_type = SignalType.HOLD
            confidence = 0.6
            reasons.append(f"Moderate overbought: RSI {rsi:.1f} > 70")
            reasons.append(f"Price at upper BB: {current_price:.2f} >= {bb_upper:.2f}")
            
        else:
            signal_type = SignalType.HOLD
            confidence = 0.2
            reasons.append(f"Price near BB middle: {current_price:.2f} ≈ {bb_middle:.2f}")
            reasons.append(f"RSI neutral: {rsi:.1f}")
        
        return TradingSignal(
            signal_type=signal_type,
            timestamp=timestamp,
            confidence=confidence,
            price=current_price,
            reasons=reasons,
            metadata={
                "rsi": rsi,
                "bb_upper": bb_upper,
                "bb_middle": bb_middle,
                "bb_lower": bb_lower,
                "bb_position": price_bb_position,
                "mean_reversion_score": abs(price_bb_position) * (abs(rsi - 50) / 50)
            }
        ) 