"""
================================================================================
Machine Learning Adaptive SuperTrend Strategy - 2026 Implementation
================================================================================

Core Innovation: Adaptive SuperTrend using K-Means Clustering for Volatility Regime Detection

This script implements the cutting-edge trend indicator methodology that combines:
1. Traditional SuperTrend logic
2. K-Means clustering for volatility regime classification
3. Adaptive parameter adjustment based on market state
4. Machine Learning-driven trend prediction

Author: JARVIS
Date: 2026-02-16
Reference: FMZ Quant Strategy & ComSIA 2026 Research
================================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Set style for better visualizations
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class MLAdaptiveSuperTrend:
    """
    Machine Learning Adaptive SuperTrend Indicator
    
    Core Logic:
    1. Calculate volatility metrics (ATR, returns std, range ratio)
    2. Use K-Means to classify market into 3 volatility regimes
    3. Adjust SuperTrend parameters adaptively based on regime
    4. Generate trend signals with regime-aware sensitivity
    """
    
    def __init__(self, n_clusters=3, lookback_period=14):
        """
        Initialize the ML Adaptive SuperTrend
        
        Parameters:
        -----------
        n_clusters : int
            Number of volatility regimes (default: 3 - Low, Medium, High)
        lookback_period : int
            Period for ATR calculation (default: 14)
        """
        self.n_clusters = n_clusters
        self.lookback_period = lookback_period
        self.kmeans = None
        self.scaler = StandardScaler()
        
        # Adaptive SuperTrend parameters for each regime
        # Format: {regime: {'multiplier': X, 'period': Y}}
        self.regime_params = {
            0: {'multiplier': 3.0, 'period': 10},  # Low volatility - wider bands
            1: {'multiplier': 2.0, 'period': 14},  # Medium volatility - balanced
            2: {'multiplier': 1.5, 'period': 7},   # High volatility - tighter bands
        }
    
    def calculate_atr(self, high, low, close, period):
        """Calculate Average True Range"""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr
    
    def calculate_volatility_features(self, data):
        """
        Calculate multiple volatility features for clustering
        
        Returns:
        --------
        DataFrame with volatility features
        """
        df = data.copy()
        
        # ATR (Average True Range)
        df['atr'] = self.calculate_atr(df['high'], df['low'], df['close'], 
                                        self.lookback_period)
        
        # Returns volatility
        df['returns'] = df['close'].pct_change()
        df['returns_std'] = df['returns'].rolling(window=self.lookback_period).std()
        
        # Price range ratio (high-low)/close
        df['range_ratio'] = (df['high'] - df['low']) / df['close']
        df['range_ratio_ma'] = df['range_ratio'].rolling(window=self.lookback_period).mean()
        
        # Bollinger Band width
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_width'] = (df['bb_std'] * 2) / df['bb_middle']
        
        return df
    
    def fit_volatility_regimes(self, data):
        """
        Use K-Means clustering to identify volatility regimes
        
        Parameters:
        -----------
        data : DataFrame
            OHLCV data
        """
        # Calculate volatility features
        df = self.calculate_volatility_features(data)
        
        # Select features for clustering
        features = df[['atr', 'returns_std', 'range_ratio_ma', 'bb_width']].dropna()
        
        # Normalize features
        features_scaled = self.scaler.fit_transform(features)
        
        # Fit K-Means
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        self.kmeans.fit(features_scaled)
        
        # Assign regime labels (0=Low, 1=Medium, 2=High volatility)
        regimes = self.kmeans.predict(features_scaled)
        
        # Sort regimes by average volatility (0=lowest, 2=highest)
        regime_volatility = []
        for i in range(self.n_clusters):
            mask = regimes == i
            avg_atr = features.loc[features.index[mask], 'atr'].mean()
            regime_volatility.append((i, avg_atr))
        
        regime_volatility.sort(key=lambda x: x[1])
        regime_mapping = {old: new for new, (old, _) in enumerate(regime_volatility)}
        
        # Remap regimes - convert to int and fill NaN with 1 (medium volatility)
        df['volatility_regime'] = pd.Series(regimes, index=features.index).map(regime_mapping).astype(int)
        
        # Forward fill missing values
        df['volatility_regime'] = df['volatility_regime'].fillna(1).astype(int)
        
        return df
    
    def calculate_adaptive_supertrend(self, data):
        """
        Calculate Adaptive SuperTrend with regime-based parameters
        
        Parameters:
        -----------
        data : DataFrame
            OHLCV data with volatility regimes
            
        Returns:
        --------
        DataFrame with SuperTrend signals
        """
        df = data.copy()
        
        # Fill any NaN values in volatility_regime with medium (1)
        df['volatility_regime'] = df['volatility_regime'].fillna(1).astype(int)
        
        # Initialize arrays
        supertrend = np.zeros(len(df))
        direction = np.zeros(len(df))  # 1 = uptrend, -1 = downtrend
        
        # Calculate for each row with adaptive parameters
        for i in range(self.lookback_period, len(df)):
            regime = int(df['volatility_regime'].iloc[i])
            params = self.regime_params[regime]
            
            # Calculate ATR with regime-specific period
            period = params['period']
            if i >= period:
                high_slice = df['high'].iloc[i-period+1:i+1]
                low_slice = df['low'].iloc[i-period+1:i+1]
                close_slice = df['close'].iloc[i-period:i]
                
                high_low = high_slice - low_slice
                high_close = np.abs(high_slice.values - close_slice.values)
                low_close = np.abs(low_slice.values - close_slice.values)
                
                true_range = pd.concat([
                    pd.Series(high_low.values),
                    pd.Series(high_close),
                    pd.Series(low_close)
                ], axis=1).max(axis=1)
                
                atr = true_range.mean()
                multiplier = params['multiplier']
                
                # Calculate basic bands
                hl2 = (df['high'].iloc[i] + df['low'].iloc[i]) / 2
                upper_band = hl2 + multiplier * atr
                lower_band = hl2 - multiplier * atr
                
                # SuperTrend logic
                if i == self.lookback_period:
                    supertrend[i] = lower_band
                    direction[i] = 1
                else:
                    prev_supertrend = supertrend[i-1]
                    prev_direction = direction[i-1]
                    
                    if prev_direction == 1:  # Currently uptrend
                        if df['close'].iloc[i] < prev_supertrend:
                            # Trend reversal
                            supertrend[i] = upper_band
                            direction[i] = -1
                        else:
                            # Continue uptrend
                            supertrend[i] = max(lower_band, prev_supertrend)
                            direction[i] = 1
                    else:  # Currently downtrend
                        if df['close'].iloc[i] > prev_supertrend:
                            # Trend reversal
                            supertrend[i] = lower_band
                            direction[i] = 1
                        else:
                            # Continue downtrend
                            supertrend[i] = min(upper_band, prev_supertrend)
                            direction[i] = -1
        
        df['adaptive_supertrend'] = supertrend
        df['trend_direction'] = direction
        
        return df
    
    def generate_signals(self, data):
        """
        Generate trading signals based on Adaptive SuperTrend
        
        Returns:
        --------
        DataFrame with signals
        """
        df = self.calculate_adaptive_supertrend(data)
        
        # Generate signals
        df['signal'] = 0
        df.loc[df['trend_direction'] == 1, 'signal'] = 1  # Buy signal
        df.loc[df['trend_direction'] == -1, 'signal'] = -1  # Sell signal
        
        # Mark crossovers
        df['signal_change'] = df['signal'].diff()
        df['buy_signal'] = (df['signal_change'] == 2).astype(int)
        df['sell_signal'] = (df['signal_change'] == -2).astype(int)
        
        return df


def generate_synthetic_price_data(days=252, starting_price=100):
    """
    Generate synthetic price data with different market regimes
    
    Parameters:
    -----------
    days : int
        Number of days of data
    starting_price : float
        Starting price
    
    Returns:
    --------
    DataFrame with OHLCV data
    """
    np.random.seed(42)
    
    # Create different regimes
    regime_days = days // 3
    
    # Regime 1: Low volatility, uptrend
    returns1 = np.random.normal(0.0005, 0.01, regime_days)
    
    # Regime 2: High volatility, sideways
    returns2 = np.random.normal(0.0000, 0.025, regime_days)
    
    # Regime 3: Medium volatility, downtrend
    returns3 = np.random.normal(-0.0003, 0.015, days - 2 * regime_days)
    
    returns = np.concatenate([returns1, returns2, returns3])
    
    # Generate price
    close = starting_price * (1 + returns).cumprod()
    
    # Generate OHLC
    high = close * (1 + np.abs(np.random.normal(0, 0.005, days)))
    low = close * (1 - np.abs(np.random.normal(0, 0.005, days)))
    open_price = close.copy()
    open_price[1:] = close[:-1]
    
    # Generate volume
    volume = np.random.randint(1000000, 5000000, days)
    
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    
    df.index = pd.date_range(start='2025-01-01', periods=days, freq='D')
    
    return df


def visualize_ml_adaptive_supertrend(data, result_df):
    """
    Create comprehensive visualizations of the ML Adaptive SuperTrend
    """
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 16))
    
    # Plot 1: Price with Adaptive SuperTrend
    ax1 = plt.subplot(4, 2, (1, 2))
    ax1.plot(data.index, data['close'], label='Price', linewidth=1.5, alpha=0.7, color='gray')
    
    # Color by trend direction
    uptrend_mask = result_df['trend_direction'] == 1
    downtrend_mask = result_df['trend_direction'] == -1
    
    ax1.plot(result_df.index[uptrend_mask], 
             result_df['adaptive_supertrend'][uptrend_mask], 
             label='SuperTrend (Uptrend)', linewidth=2, color='#2ecc71', alpha=0.8)
    ax1.plot(result_df.index[downtrend_mask], 
             result_df['adaptive_supertrend'][downtrend_mask], 
             label='SuperTrend (Downtrend)', linewidth=2, color='#e74c3c', alpha=0.8)
    
    # Mark buy/sell signals
    buy_signals = result_df[result_df['buy_signal'] == 1]
    sell_signals = result_df[result_df['sell_signal'] == 1]
    
    ax1.scatter(buy_signals.index, buy_signals['close'], 
                marker='^', color='#2ecc71', s=200, label='Buy Signal', zorder=5)
    ax1.scatter(sell_signals.index, sell_signals['close'], 
                marker='v', color='#e74c3c', s=200, label='Sell Signal', zorder=5)
    
    ax1.set_title('ML Adaptive SuperTrend Strategy', fontsize=16, fontweight='bold')
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Price', fontsize=12)
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Volatility Regimes
    ax2 = plt.subplot(4, 2, 3)
    regime_colors = {0: '#3498db', 1: '#f39c12', 2: '#e74c3c'}
    regime_names = {0: 'Low Volatility', 1: 'Medium Volatility', 2: 'High Volatility'}
    
    for regime in range(3):
        mask = result_df['volatility_regime'] == regime
        ax2.scatter(result_df.index[mask], 
                   result_df['atr'][mask], 
                   c=regime_colors[regime], 
                   label=regime_names[regime], 
                   alpha=0.6, s=20)
    
    ax2.set_title('K-Means Volatility Regime Classification', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=11)
    ax2.set_ylabel('ATR (Average True Range)', fontsize=11)
    ax2.legend(loc='best', fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Regime Distribution
    ax3 = plt.subplot(4, 2, 4)
    regime_counts = result_df['volatility_regime'].value_counts().sort_index()
    colors = [regime_colors[i] for i in regime_counts.index]
    bars = ax3.bar([regime_names[i] for i in regime_counts.index], 
                   regime_counts.values, 
                   color=colors, 
                   alpha=0.7, 
                   edgecolor='black')
    ax3.set_title('Market Regime Distribution', fontsize=14, fontweight='bold')
    ax3.set_ylabel('Number of Days', fontsize=11)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Add count labels on bars
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Plot 4: ATR Over Time
    ax4 = plt.subplot(4, 2, 5)
    ax4.plot(result_df.index, result_df['atr'], 
             color='#9b59b6', linewidth=1.5, label='ATR')
    ax4.axhline(result_df['atr'].mean(), 
                color='red', linestyle='--', 
                label=f'Mean: {result_df["atr"].mean():.2f}', alpha=0.7)
    ax4.fill_between(result_df.index, 0, result_df['atr'], alpha=0.3, color='#9b59b6')
    ax4.set_title('Average True Range (ATR) - Volatility Metric', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Date', fontsize=11)
    ax4.set_ylabel('ATR', fontsize=11)
    ax4.legend(loc='best', fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    # Plot 5: Returns Distribution by Regime
    ax5 = plt.subplot(4, 2, 6)
    for regime in range(3):
        mask = result_df['volatility_regime'] == regime
        returns = result_df['returns'][mask].dropna()
        ax5.hist(returns, bins=30, alpha=0.5, 
                color=regime_colors[regime], 
                label=regime_names[regime], 
                density=True)
    
    ax5.set_title('Returns Distribution by Volatility Regime', fontsize=14, fontweight='bold')
    ax5.set_xlabel('Daily Returns', fontsize=11)
    ax5.set_ylabel('Density', fontsize=11)
    ax5.legend(loc='best', fontsize=9)
    ax5.grid(True, alpha=0.3, axis='y')
    
    # Plot 6: Adaptive Parameters Over Time
    ax6 = plt.subplot(4, 2, 7)
    multipliers = result_df['volatility_regime'].map(
        lambda x: {0: 3.0, 1: 2.0, 2: 1.5}[x]
    )
    ax6.plot(result_df.index, multipliers, 
             color='#e67e22', linewidth=1.5, drawstyle='steps-post')
    ax6.set_title('Adaptive Multiplier Parameter', fontsize=14, fontweight='bold')
    ax6.set_xlabel('Date', fontsize=11)
    ax6.set_ylabel('Multiplier', fontsize=11)
    ax6.set_yticks([1.5, 2.0, 3.0])
    ax6.set_yticklabels(['1.5 (High Vol)', '2.0 (Med Vol)', '3.0 (Low Vol)'])
    ax6.grid(True, alpha=0.3)
    
    # Plot 7: Performance Metrics
    ax7 = plt.subplot(4, 2, 8)
    ax7.axis('off')
    
    # Calculate performance metrics
    signals = result_df['signal'].dropna()
    returns = result_df['returns'].dropna()
    strategy_returns = signals.shift(1) * returns
    
    total_trades = result_df['buy_signal'].sum() + result_df['sell_signal'].sum()
    final_return = (1 + strategy_returns.fillna(0)).prod() - 1
    
    metrics_text = f"""
    ============================================
       ML Adaptive SuperTrend Metrics
    ============================================
    Total Trading Days: {len(data):>8}
    Total Trades: {int(total_trades):>13}
                                   
    Strategy Return: {final_return:>9.2%}
    Buy/Sell Ratio: {result_df['buy_signal'].sum()/(result_df['sell_signal'].sum()+1):>9.2f}
                                   
    Avg ATR: {result_df['atr'].mean():>10.4f}
    Max ATR: {result_df['atr'].max():>10.4f}
    Min ATR: {result_df['atr'].min():>10.4f}
    ============================================
    """
    
    ax7.text(0.1, 0.5, metrics_text, 
             fontsize=12, fontfamily='monospace',
             verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    plt.tight_layout()
    
    # Save figure
    output_path = r'C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\reports\ml_adaptive_supertrend_2026.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"[OK] Visualization saved: {output_path}")
    
    return fig


def main():
    """
    Main execution function
    """
    print("=" * 80)
    print("ML ADAPTIVE SUPERTREND STRATEGY - 2026 IMPLEMENTATION")
    print("=" * 80)
    print()
    
    # Step 1: Generate synthetic price data
    print("[INFO] Step 1: Generating synthetic price data with multiple regimes...")
    data = generate_synthetic_price_data(days=252, starting_price=100)
    print(f"  [OK] Data generated: {len(data)} days")
    print(f"  [INFO] Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
    print()
    
    # Step 2: Initialize ML Adaptive SuperTrend
    print("[INFO] Step 2: Initializing ML Adaptive SuperTrend indicator...")
    adapter = MLAdaptiveSuperTrend(n_clusters=3, lookback_period=14)
    print("  [OK] K-Means clustering configured for 3 volatility regimes")
    print("  [OK] Adaptive parameter mapping initialized")
    print()
    
    # Step 3: Fit volatility regimes
    print("[INFO] Step 3: Identifying volatility regimes using K-Means clustering...")
    result_df = adapter.fit_volatility_regimes(data)
    
    regime_counts = result_df['volatility_regime'].value_counts().sort_index()
    regime_names = {0: 'Low Volatility', 1: 'Medium Volatility', 2: 'High Volatility'}
    print("  [OK] Volatility regimes identified:")
    for i, count in regime_counts.items():
        i = int(i)  # Convert to int
        print(f"     - {regime_names[i]}: {count} days ({count/len(result_df)*100:.1f}%)")
    print()
    
    # Step 4: Calculate Adaptive SuperTrend
    print("[INFO] Step 4: Calculating Adaptive SuperTrend with regime-based parameters...")
    result_df = adapter.calculate_adaptive_supertrend(result_df)
    print("  [OK] SuperTrend calculated with adaptive multipliers:")
    print("     - Low Volatility: 3.0 (wider bands)")
    print("     - Medium Volatility: 2.0 (balanced)")
    print("     - High Volatility: 1.5 (tighter bands)")
    print()
    
    # Step 5: Generate trading signals
    print("[INFO] Step 5: Generating trading signals...")
    result_df = adapter.generate_signals(result_df)
    
    buy_signals = result_df['buy_signal'].sum()
    sell_signals = result_df['sell_signal'].sum()
    print(f"  [OK] Buy signals generated: {int(buy_signals)}")
    print(f"  [OK] Sell signals generated: {int(sell_signals)}")
    print()
    
    # Step 6: Calculate performance
    print("[INFO] Step 6: Calculating strategy performance...")
    signals = result_df['signal'].dropna()
    returns = result_df['returns'].dropna()
    strategy_returns = signals.shift(1) * returns
    final_return = (1 + strategy_returns.fillna(0)).prod() - 1
    print(f"  [OK] Strategy Return: {final_return:.2%}")
    print()
    
    # Step 7: Visualize results
    print("[INFO] Step 7: Creating comprehensive visualizations...")
    fig = visualize_ml_adaptive_supertrend(data, result_df)
    print("  [OK] 7-panel visualization created")
    print()
    
    # Step 8: Summary
    print("=" * 80)
    print("ML ADAPTIVE SUPERTREND STRATEGY - EXECUTION COMPLETE")
    print("=" * 80)
    print()
    print("KEY INNOVATIONS:")
    print("  1. K-Means clustering for automatic volatility regime detection")
    print("  2. Adaptive parameter adjustment based on market state")
    print("  3. Dynamic SuperTrend bands responsive to volatility changes")
    print("  4. Machine Learning-driven trend identification")
    print()
    print("OUTPUT FILES:")
    print("  - Visualization: ml_adaptive_supertrend_2026.png")
    print()
    print("USAGE:")
    print("  - Apply to real market data for live trading")
    print("  - Optimize clustering parameters for specific instruments")
    print("  - Combine with other indicators for confirmation")
    print("  - Backtest thoroughly before deployment")
    print()
    print("=" * 80)
    
    return result_df


if __name__ == "__main__":
    # Execute the strategy
    results = main()
    
    print()
    print("Next steps:")
    print("  1. Backtest on historical data")
    print("  2. Optimize parameters for your market")
    print("  3. Implement risk management")
    print("  4. Deploy to paper trading first")