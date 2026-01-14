import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from wordcloud import WordCloud, STOPWORDS
import io
import base64
from parse_and_clean import parse_and_clean_discord_txt
import sys
import os

def get_top_contributors_chart(df, top_n=10):
    """
    Generates a horizontal bar chart of the top contributors.
    Returns the HTML div string of the chart.
    """
    if df.empty:
        return "<p>No messages found.</p>"

    # Filter out generic unknown users (case-insensitive)
    ignored_users = {'sconosciuto', 'unknown'}
    df_filtered = df[~df['user'].astype(str).str.lower().isin(ignored_users)]

    user_counts = df_filtered['user'].value_counts().head(top_n)
    
    # Sort for better visualization (highest on top)
    user_counts = user_counts.sort_values(ascending=True)

    # Convert to standard lists to ensure Plotly serializes correctly
    x_values = user_counts.values.tolist()
    y_values = user_counts.index.tolist()

    fig = go.Figure(go.Bar(
        x=x_values,
        y=y_values,
        orientation='h',
        marker=dict(
            color=x_values,
            colorscale='Plasma',
            showscale=False
        ),
        text=x_values,
        textposition='auto'
    ))

    fig.update_layout(
        xaxis_title="Messages",
        yaxis_title=None,
        yaxis=dict(automargin=True),
        xaxis=dict(automargin=True),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=500,
        margin=dict(t=30, b=30, r=20),
        font=dict(family="Segoe UI, sans-serif"),
        autosize=True
    )

    # Return just the div. Plotly.js is loaded in the template header.
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id='top_contributors_chart', config={'responsive': True})

def get_activity_heatmap(df):
    """
    Generates a heatmap of activity by Day of Week vs Hour of Day.
    Returns the HTML div string of the chart.
    """
    if df.empty:
        return "<p>No data for heatmap.</p>"

    # Ensure timestamp is datetime
    # Use .loc to avoid SettingWithCopyWarning if df is a slice
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Extract day and hour
    # Use dayofweek (0=Monday, 6=Sunday) to be locale-safe
    df['day_idx'] = df['timestamp'].dt.dayofweek
    df['hour'] = df['timestamp'].dt.hour
    
    # Group by day index and hour
    heatmap_data = df.groupby(['day_idx', 'hour']).size().reset_index(name='count')


    # Pivot for heatmap format (Days on y-axis, Hours on x-axis)
    pivot_table = heatmap_data.pivot(index='day_idx', columns='hour', values='count').fillna(0)

    # Reindex to ensure all days (0-6) and hours (0-23) are present
    pivot_table = pivot_table.reindex(index=range(7), fill_value=0)
    pivot_table = pivot_table.reindex(columns=range(24), fill_value=0)
    
    # Map index to names for display
    days_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_table.values.tolist(), 
        x=list(range(24)),
        y=days_names, 
        colorscale='Viridis', 
        hoverongaps=False
    ))
    
    fig.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title=None,
        yaxis=dict(autorange="reversed", automargin=True), # Puts Monday (index 0) at the top
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(t=30, b=30),
        font=dict(family="Segoe UI, sans-serif")
    )
    
    # plotly.js is already included by the first chart (or in template), so we can say include_plotlyjs=False 
    # BUT keeping it 'cdn' or True is safer if charts are rendered independently. 
    # However, for multiple charts on one page, duplication is bad.
    # The first chart (contributors) sets include_plotlyjs='cdn'.
    # We will set include_plotlyjs=False here assuming the first one loads it, 
    # OR we can just rely on the template loading it via script tag if we want to be clean.
    # The previous code set include_plotlyjs='cdn' in get_top_contributors_chart.
    # To follow the pattern, we'll set it to False here and assume the first one handles it, 
    # or better, rely on the template. But since the template hasn't explicitly added the script tag 
    # (it relied on the python output), let's stick with 'cdn' but maybe the template should handle it.
    
    # It's safer to include it again? No, that causes issues.
    # Actually, plot_top_contributors returns include_plotlyjs='cdn'.
    # If we put two charts, the second one shouldn't need to load it again if it's the same lib.
    # But usually 'cdn' checks if it's already there? No, it emits the script tag.
    # Let's change strictly to False here and trust the first chart, 
    # OR change both to False and add the script to the template head.
    
    # Let's keep it consistent: include_plotlyjs=False here.
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id='activity_heatmap', config={'responsive': True})

def get_wordcloud_img(df):
    """
    Generates a Word Cloud from message content.
    Returns an HTML <img> tag string with the base64 encoded image.
    """
    # 'message' is the column name from parse_and_clean.py
    target_col = 'message' if 'message' in df.columns else 'content'
    
    if df.empty or target_col not in df.columns:
        return "<p class='text-gray-400'>No content available for Word Cloud.</p>"

    # Combine text
    # Filter out empty or NaN content
    text_series = df[target_col].dropna().astype(str)
    text = " ".join(text_series.tolist())
    
    if not text.strip():
         return "<p class='text-gray-400'>Not enough text for Word Cloud.</p>"

    # Simple stopword extension (basic Italian + English defaults)
    custom_stopwords = set(STOPWORDS)
    
    # Load Italian Stopwords from file
    stopwords_path = os.path.join(os.path.dirname(__file__), 'resources', 'italian_stopwords.txt')
    if os.path.exists(stopwords_path):
        try:
            with open(stopwords_path, 'r', encoding='utf-8') as f:
                file_stopwords = {line.strip().lower() for line in f if line.strip()}
            custom_stopwords.update(file_stopwords)
        except Exception as e:
            print(f"[WARN] Failed to load stopwords from file: {e}")
    else:
        print(f"[WARN] Stopwords file not found at {stopwords_path}. using hardcoded defaults.")
        # Fallback to hardcoded list if file missing
        italian_stopwords = {
            'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'una', 'uno',
            'e', 'ed', 'o', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
            'di', 'del', 'dello', 'della', 'dei', 'degli', 'delle',
            'ad', 'al', 'allo', 'alla', 'ai', 'agli', 'alle',
            'nel', 'nello', 'nella', 'nei', 'negli', 'nelle',
            'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle',
            'che', 'chi', 'cui', 'non', 'più', 'quale', 'quanto', 'quanta',
            'io', 'tu', 'lui', 'lei', 'noi', 'voi', 'loro',
            'mio', 'mia', 'tuo', 'tua', 'suo', 'sua', 'nostro', 'nostra',
            'vostro', 'vostra', 'è', 'ha', 'ho', 'sono', 'sei', 'siamo', 'siete',
            'hanno', 'c', 'l', 'se', 'ma', 'anche', 'comunque', 'però', 'quindi',
            'infatti', 'invece', 'allora', 'così', 'cosa', 'come', 'dove', 'quando',
            'perché', 'poiché', 'mentre', 'finché', 'dopo', 'prima', 'poi', 'ora',
            'adesso', 'qui', 'lì', 'là', 'su', 'giù', 'dentro', 'fuori',
            'tutto', 'tutta', 'tutti', 'tutte', 'altro', 'altra', 'altri', 'altre',
            'molto', 'molta', 'molti', 'molte', 'poco', 'poca', 'pochi', 'poche',
            'tanto', 'tanta', 'tanti', 'tante', 'troppo', 'troppa', 'troppi', 'troppe',
            'stesso', 'stessa', 'stessi', 'stesse',
            'fa', 'fatto', 'fare', 'faccio', 'facciamo', 'fanno',
            'va', 'vado', 'andare', 'andiamo', 'vanno',
            'url', 'http', 'https', 'www', 'com', 'it', 'net', 'org', 'discord', 'utenza',
            'user', 'message', 'deleted', 'attachment'
        }
        custom_stopwords.update(italian_stopwords)
    
    # Always add tech/discord specific terms
    tech_stopwords = {
        'url', 'http', 'https', 'www', 'com', 'it', 'net', 'org', 'discord', 'utenza',
        'user', 'message', 'deleted', 'attachment'
    }
    custom_stopwords.update(tech_stopwords)

    try:
        # Generate word cloud
        wc = WordCloud(
            width=1000, 
            height=500, 
            background_color="#101010", # Very dark grey, matching Plotly Dark
            colormap="plasma",
            stopwords=custom_stopwords,
            min_font_size=10,
            max_words=200,
            random_state=42
        ).generate(text)
        
        # Convert to image
        img = wc.to_image()
        
        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        html_img = f'<div class="flex justify-center p-4"><img src="data:image/png;base64,{img_b64}" alt="Word Cloud" style="width:100%; max-width:1000px; height:auto; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);"></div>'
        return html_img
        
    except Exception as e:
        print(f"Error generating word cloud: {e}")
        return f"<p class='text-red-500'>Error generating word cloud: {e}</p>"

def get_timeline_chart(df):
    """
    Generates a time-series line chart of message activity (Daily).
    Returns the HTML div string of the chart.
    """
    if df.empty or 'timestamp' not in df.columns:
        return "<p>No time data available.</p>"

    # Ensure valid datetime
    # We work on a copy to avoid SettingWithCopy warnings if df is a slice
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df_valid = df.dropna(subset=['timestamp'])

    if df_valid.empty:
         return "<p>No valid timestamps found.</p>"

    # Group by Normalized Timestamp (Midnight)
    # This ensures keys are Timestamps (datetime64[ns]), not datetime.date objects
    daily_counts = df_valid.groupby(df_valid['timestamp'].dt.normalize()).size()
    
    # Fill missing dates to ensure continuity for Moving Average
    if daily_counts.empty:
         return "<p>No data to plot.</p>"

    idx = pd.date_range(daily_counts.index.min(), daily_counts.index.max())
    daily_counts = daily_counts.reindex(idx, fill_value=0)
    
    dates = daily_counts.index # DatetimeIndex
    counts = daily_counts.values # numpy array
    
    # Calculate Moving Average (7 Day)
    # We use min_periods=1 so we don't have NaNs at the start
    rolling_avg = pd.Series(counts).rolling(window=7, min_periods=1).mean()
    
    # Convert dates to list of strings to separate it completely from any index logic
    date_strs = dates.strftime('%Y-%m-%d').tolist()
    # Convert counts to list
    counts_list = counts.tolist()
    # Convert rolling to list, handling nan
    rolling_list = rolling_avg.fillna(0).tolist()
    
    fig = go.Figure()

    # Raw Data (Faint Background)
    fig.add_trace(go.Scatter(
        x=date_strs, 
        y=counts_list,
        mode='lines', 
        name='Daily Raw',
        line=dict(color='rgba(59, 130, 246, 0.3)', width=1), # Faint Blue
        fill='tozeroy', 
        fillcolor='rgba(59, 130, 246, 0.05)', # Very faint fill
        hoverinfo='skip'
    ))

    # Moving Average (Main Line)
    fig.add_trace(go.Scatter(
        x=date_strs, 
        y=rolling_list, 
        mode='lines', 
        name='7-Day Average',
        line=dict(color='#60A5FA', width=3) # Lighter Blue (Tailwind Blue-400)
    ))


    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Messages",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=450,
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(family="Segoe UI, sans-serif"),
        autosize=True, # Ensure it adapts to container width
        xaxis=dict(
            showgrid=False,
            automargin=True # crucial for half-width
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            automargin=True
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig.to_html(full_html=False, include_plotlyjs=False, div_id='timeline_chart', config={'responsive': True})

def get_yap_o_meter_chart(df):
    """
    Analyzes message verbosity.
    Returns HTML div of subplots: Longest Avg Length vs Shortest Avg Length.
    """
    if df.empty:
        return "<p>No data for Yap-o-meter.</p>"
    
    # Calculate length
    # Using 'message' column
    df = df.copy()
    col = 'message' if 'message' in df.columns else 'content'
    # Ensure strings
    df[col] = df[col].astype(str)
    df['char_count'] = df[col].str.len()
    
    # Filter out generic users
    ignored_users = {'sconosciuto', 'unknown', 'deleted user'}
    df_filtered = df[~df['user'].astype(str).str.lower().isin(ignored_users)]
    
    # Group
    stats = df_filtered.groupby('user')['char_count'].agg(['mean', 'count'])
    
    # Filter: Users must have > 10 messages for stats to have meaning
    stats = stats[stats['count'] > 10]
    
    if stats.empty:
         return "<p>Not enough user data (min 10 messages) for Yap-o-meter.</p>"
         
    # Top 5 Longest (The Novelists)
    # Sort descending by mean, take top 5, then reverse for plot (so largest is at top)
    novelist = stats.sort_values('mean', ascending=False).head(5).iloc[::-1]
    
    # Top 5 Shortest (One-worders)
    # Sort ascending by mean, take top 5, then reverse for plot (so smallest is at top of its graph? No, usually smallest bar last.)
    # Let's say we want the #1 One-worder at the top. 
    # Smallest mean = #1 One-worder.
    one_worders = stats.sort_values('mean', ascending=True).head(5).iloc[::-1]

    # Create Subplots (ROWS=2, COLS=1)
    fig = make_subplots(
        rows=2, cols=1, 
        subplot_titles=("📜 The Novelists (Longest Avg Msg)", "🤐 The Ultra-Concise (Shortest Avg Msg)"),
        vertical_spacing=0.25
    )

    # Novelists Bar
    fig.add_trace(
        go.Bar(
            y=novelist.index.tolist(), 
            x=novelist['mean'].tolist(), 
            orientation='h',
            name='Avg Chars',
            marker=dict(color=novelist['mean'].tolist(), colorscale='Plasma'),
            text=novelist['mean'].round(1).tolist(),
            textposition='auto',
            customdata=novelist['count'].tolist(),
            hovertemplate="<b>%{y}</b><br>Avg: %{x:.1f} chars<br>Count: %{customdata} msgs<extra></extra>",
            showlegend=False
        ),
        row=1, col=1
    )

    # One-worders Bar
    fig.add_trace(
        go.Bar(
            y=one_worders.index.tolist(), 
            x=one_worders['mean'].tolist(), 
            orientation='h',
            name='Avg Chars',
            marker=dict(color=one_worders['mean'].tolist(), colorscale='Tealgrn'), 
            text=one_worders['mean'].round(1).tolist(),
            textposition='auto',
            customdata=one_worders['count'].tolist(),
            hovertemplate="<b>%{y}</b><br>Avg: %{x:.1f} chars<br>Count: %{customdata} msgs<extra></extra>",
            showlegend=False
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=800, # Increased height to prevent overlap
        margin=dict(t=60, b=30, r=20),
        font=dict(family="Segoe UI, sans-serif"),
        autosize=True
    )
    
    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)
    
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id='yap_chart', config={'responsive': True})

def get_night_owls_chart(df):
    """
    Categorizes users by time of day activity.
    Night (0-6), Morning (6-12), Afternoon (12-18), Evening (18-00).
    Stacked Bar Chart for Top 10 Active Users.
    """
    if df.empty or 'timestamp' not in df.columns:
        return "<p>No time data available.</p>"
        
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    
    # Filter generic users
    ignored_users = {'sconosciuto', 'unknown', 'deleted user'}
    df = df[~df['user'].astype(str).str.lower().isin(ignored_users)]
    
    # Get Top 10 Users by volume
    top_users = df['user'].value_counts().head(10).index
    df_top = df[df['user'].isin(top_users)].copy()
    
    if df_top.empty:
        return "<p>Not enough data for Night Owls.</p>"
        
    df_top['hour'] = df_top['timestamp'].dt.hour
    
    # Custom binning
    def get_time_category(hour):
        if 0 <= hour < 6: return 'Night (00-06)'
        if 6 <= hour < 12: return 'Morning (06-12)'
        if 12 <= hour < 18: return 'Afternoon (12-18)'
        return 'Evening (18-24)'
        
    df_top['time_category'] = df_top['hour'].apply(get_time_category)
    
    # Pivot: Index=User, Col=Category, Val=Count
    pivot_count = pd.crosstab(df_top['user'], df_top['time_category'])
    
    # Calculate percentages (row-wise normalization * 100)
    pivot_pct = pivot_count.div(pivot_count.sum(axis=1), axis=0) * 100
    
    # Reorder columns
    ordered_cols = ['Night (00-06)', 'Morning (06-12)', 'Afternoon (12-18)', 'Evening (18-24)']
    
    # Ensure all cols exist in both dataframes
    for c in ordered_cols:
        if c not in pivot_pct.columns:
            pivot_pct[c] = 0.0
        if c not in pivot_count.columns:
            pivot_count[c] = 0

    pivot_pct = pivot_pct[ordered_cols]
    pivot_count = pivot_count[ordered_cols]
    
    # Sort users by "Night" percentage descending to highlight the owls
    # (Plotly draws y-axis from bottom to top, so ascending sort puts smallest at bottom. 
    # We want largest Night Owl at the top? No, usually top of chart.
    # If we want largest Night Owl at TOP of chart, we need it at the END of the list passed to y.
    # So we sort ascending.)
    pivot_pct = pivot_pct.sort_values('Night (00-06)', ascending=True)
    
    # Align counts order to the sorted percentages
    pivot_count = pivot_count.reindex(pivot_pct.index)
    
    fig = go.Figure()
    
    colors = {
        'Night (00-06)': '#8B5CF6',    # Violet
        'Morning (06-12)': '#FBBF24',  # Amber
        'Afternoon (12-18)': '#F87171', # Red
        'Evening (18-24)': '#60A5FA'   # Blue
    }
    
    # Explicitly convert to lists to ensure Plotly renders correctly without Index mismatches
    y_users = pivot_pct.index.tolist()
    
    for cat in ordered_cols:
        x_vals = pivot_pct[cat].tolist()
        count_vals = pivot_count[cat].astype(int).tolist()
        
        # detailed hover info
        hover_text = [f"{v:.1f}%<br>({c} msgs)" for v, c in zip(x_vals, count_vals)]
        
        fig.add_trace(go.Bar(
            y=y_users,
            x=x_vals,
            name=cat,
            orientation='h',
            marker_color=colors[cat],
            text=hover_text,
            hovertemplate="<b>%{y}</b><br>" + cat + ": %{text}<extra></extra>"
        ))
        
    fig.update_layout(
        barmode='stack',
        xaxis_title="Activity %",
        title="Active Times for Top 10 Users",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        margin=dict(t=60, b=30, r=20), 
        yaxis=dict(automargin=True),
        xaxis=dict(range=[0, 105], fixedrange=True), # Force 0-100% scale
        font=dict(family="Segoe UI, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        autosize=True
    )
    
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id='night_owls_chart', config={'responsive': True})

def get_spammer_chart(df, top_n=10):
    """
    Identifies users who share the most links (http/https).
    Returns the HTML div string of the chart.
    """
    if df.empty or 'message' not in df.columns:
        return "<p>No data for Spammer Stats.</p>"

    link_msgs = df[df['message'].astype(str).str.contains("http", case=False, na=False)]
    
    if link_msgs.empty:
        return "<p>No links found in chat.</p>"

    # Filter out generic unknown users (case-insensitive) for Spammer chart too
    ignored_users = {'sconosciuto', 'unknown', 'deleted user'}
    link_msgs = link_msgs[~link_msgs['user'].astype(str).str.lower().isin(ignored_users)]

    spammer_counts = link_msgs['user'].value_counts().head(top_n)
    spammer_counts = spammer_counts.sort_values(ascending=True)

    # Convert to standard lists to ensure Plotly serializes correctly
    x_vals = spammer_counts.values.tolist()
    y_vals = spammer_counts.index.tolist()

    fig = go.Figure(go.Bar(
        x=x_vals,
        y=y_vals,
        orientation='h',
        marker=dict(
            color=x_vals,
            colorscale='YlOrRd', 
            showscale=False
        ),
        text=x_vals,
        textposition='auto'
    ))

    fig.update_layout(
        xaxis_title="Links Shared",
        yaxis_title=None,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(family="Segoe UI, sans-serif")
    )

    return fig.to_html(full_html=False, include_plotlyjs=False, div_id='spammer_chart')


