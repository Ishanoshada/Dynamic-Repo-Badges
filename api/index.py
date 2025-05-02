from flask import Flask, Response, request,render_template
from pymongo import MongoClient
import datetime
import statistics
from urllib.parse import unquote
import math
from os import getenv
from dotenv import load_dotenv
import random
from flask_minify import Minify

app = Flask(__name__)
Minify(app=app, html=True, js=True, cssless=True)   

# MongoDB connection setup
load_dotenv()

client = MongoClient(getenv('MONGODB_URI'))

db = client['repo_stats']
views_collection = db['repository_views']

# Sample data insertion function
def insert_sample_data(tag_name):
    """Insert sample view data for a tag if it doesn't exist"""
    if views_collection.count_documents({"tag": tag_name}) == 0:
        current_date = datetime.datetime.now()
        sample_data = [
            {
                "tag": tag_name,
                "date": current_date - datetime.timedelta(days=i),
                "views": 50 + i * 10 + (i * i)
            } for i in range(30)
        ]
        views_collection.insert_many(sample_data)
        print(f"Inserted sample data for tag: {tag_name}")


# Function to get statistics for a repository tag
def get_repo_stats(tag_name):
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)
    
    query = {
        "tag": tag_name,
        "date": {"$gte": start_date, "$lte": end_date}
    }
    
    views_data = list(views_collection.find(query).sort("date", 1))
    
    if not views_data:
        insert_sample_data(tag_name)
        views_data = list(views_collection.find(query).sort("date", 1))
    
    views_counts = [entry["views"] for entry in views_data]
    total_views = sum(views_counts)
    avg_daily = round(statistics.mean(views_counts))
    peak_views = max(views_counts)
    
    graph_data = views_data[-6:]
    graph_values = [entry["views"] for entry in graph_data]
    
    if max(graph_values) > 0:
        min_y, max_y = 85, 55
        scale_factor = (min_y - max_y) / max(graph_values)
        scaled_values = [min_y - (val * scale_factor) for val in graph_values]
    else:
        scaled_values = [70] * 6
    
    x_start = 250
    x_step = 20
    graph_points = [f"{x_start + (i * x_step)},{y}" for i, y in enumerate(scaled_values)]
    
    return {
        "total_views": total_views,
        "avg_daily": avg_daily,
        "peak_views": peak_views,
        "graph_points": " ".join(graph_points)
    }

# Function to update view count
def update_view_count(tag_name):
    """Update view count for a repository tag"""
    tag_name = unquote(tag_name)
    current_date = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    existing_entry = views_collection.find_one({"tag": tag_name, "date": current_date})
    
    if existing_entry:
        views_collection.update_one(
            {"_id": existing_entry["_id"]},
            {"$inc": {"views": 1}}
        )
    else:
        views_collection.insert_one({
            "tag": tag_name,
            "date": current_date,
            "views": 1
        })

@app.route('/svg/count/1/<path:svg_text>/<tag>')
def generate_svg(svg_text, tag):
    # Clean and decode tag
    tag = unquote(tag)
    
    # Update view count
    update_view_count(tag)
    
    # Get stats
    stats = get_repo_stats(tag)
    formatted_views = f"{stats['total_views']:,}"
    
    # Decode svg_text for display
    svg_text = unquote(svg_text)
    
    # Generate SVG
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="140" viewBox="0 0 400 140" xmlns="http://www.w3.org/2000/svg">
  <style>
    @keyframes pulse {{ 0% {{ opacity: 0.6; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.6; }} }}
    @keyframes countUp {{ from {{ stroke-dashoffset: 500; }} to {{ stroke-dashoffset: 0; }} }}
    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes rotate {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
    .bg {{ fill: #0d1117; }}
    .card {{ fill: #161b22; rx: 8; ry: 8; }}
    .title {{ font-family: monospace; font-size: 18px; font-weight: bold; fill: #c9d1d9; }}
    .count {{ font-family: monospace; font-size: 38px; font-weight: bold; fill: #58a6ff; animation: fadeIn 1s ease-out; }}
    .graph-line {{ fill: none; stroke: #39d353; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 500; animation: countUp 2s ease-out forwards; }}
    .eye {{ fill: none; stroke: #58a6ff; stroke-width: 2.5; animation: pulse 2s infinite; }}
    .eye-center {{ fill: #58a6ff; animation: pulse 2s infinite; }}
    .gear {{ transform-origin: center; animation: rotate 10s linear infinite; }}
    .gear-inner {{ fill: #30363d; stroke: #58a6ff; stroke-width: 1.5; }}
    .stat-label {{ font-family: monospace; font-size: 12px; fill: #8b949e; }}
    .stat-value {{ font-family: monospace; font-size: 12px; fill: #c9d1d9; font-weight: bold; }}
    .dot {{ fill: #39d353; animation: pulse 2s infinite; }}
    .repo-name {{ font-family: monospace; font-size: 12px; fill: #8b949e; font-style: italic; }}
  </style>
  <rect width="400" height="140" class="bg"/>
  <rect x="10" y="10" width="380" height="120" class="card"/>
  <text x="30" y="40" class="title">{svg_text}</text>
  <text x="200" y="40" class="repo-name">{tag}</text>
  <text x="30" y="85" class="count" id="viewCount">{formatted_views}</text>
  <text x="30" y="110" class="stat-label">Average: </text>
  <text x="90" y="110" class="stat-value">{stats['avg_daily']} / day</text>
  <text x="170" y="110" class="stat-label">Peak: </text>
  <text x="210" y="110" class="stat-value">{stats['peak_views']}</text>
  <circle cx="155" cy="108" r="3" class="dot"/>
  <circle cx="265" cy="108" r="3" class="dot"/>
  <polyline class="graph-line" points="{stats['graph_points']}"/>
  <g transform="translate(200, 40)">
    <circle cx="0" cy="0" r="12" class="eye"/>
    <circle cx="0" cy="0" r="4" class="eye-center"/>
  </g>
  <g class="gear" transform="translate(230, 40)">
    <path class="gear-inner" d="M0,-10 L2,-4 L8,-2 L4,2 L6,8 L0,6 L-6,8 L-4,2 L-8,-2 L-2,-4 Z"/>
    <circle cx="0" cy="0" r="3" class="gear-inner"/>
  </g>
</svg>'''

    return Response(svg, mimetype='image/svg+xml')

@app.route('/svg/count/2/<path:svg_text>/<tag>')
def generate_svg2(svg_text, tag):
    # Clean and decode tag
    tag = unquote(tag)
    
    # Update view count
    update_view_count(tag)
    
    # Get stats
    stats = get_repo_stats(tag)
    formatted_views = f"{stats['total_views']:,}"
    
    # Decode svg_text for display
    svg_text = unquote(svg_text)
    
    # Create bar chart data for the last 7 days
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    
    query = {
        "tag": tag,
        "date": {"$gte": start_date, "$lte": end_date}
    }
    
    recent_data = list(views_collection.find(query).sort("date", 1))
    
    if not recent_data:
        # Use sample data points instead
        recent_data = [{"views": stats["avg_daily"] * (0.8 + i*0.05)} for i in range(7)]
    
    # Generate bar chart
    bar_values = [entry.get("views", 0) for entry in recent_data]
    if max(bar_values) > 0:
        bar_height = 50  # Maximum bar height
        scale_factor = bar_height / max(bar_values)
        scaled_bars = [val * scale_factor for val in bar_values]
    else:
        scaled_bars = [10] * 7
    
    bar_width = 20
    bar_spacing = 10
    bar_start_x = 270
    bar_base_y = 100
    
    bar_elements = []
    for i, height in enumerate(scaled_bars):
        x = bar_start_x + i * (bar_width + bar_spacing)
        y = bar_base_y - height
        
        # Create gradient ID
        gradient_id = f"barGradient{i}"
        
        # Create bar with gradient
        bar_elements.append(f'''
    <linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#8b5cf6" />
      <stop offset="100%" stop-color="#3b82f6" />
    </linearGradient>
    <rect x="{x}" y="{y}" width="{bar_width}" height="{height}" rx="3" ry="3" fill="url(#{gradient_id})">
      <animate attributeName="height" from="0" to="{height}" dur="1s" begin="0.{i*2}s" fill="freeze" />
      <animate attributeName="y" from="{bar_base_y}" to="{y}" dur="1s" begin="0.{i*2}s" fill="freeze" />
    </rect>
    ''')
    
    # Generate SVG with modern design
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="160" viewBox="0 0 500 160" xmlns="http://www.w3.org/2000/svg">
  <style>
    @keyframes pulse {{ 0% {{ opacity: 0.8; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.8; }} }}
    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes slideIn {{ from {{ transform: translateX(-20px); opacity: 0; }} to {{ transform: translateX(0); opacity: 1; }} }}
    @keyframes countUp {{ from {{ transform: translateY(10px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
    
    .bg {{ fill: #111827; }}
    .card {{ fill: #1f2937; rx: 12; ry: 12; filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1)); }}
    .title {{ font-family: system-ui, -apple-system, sans-serif; font-size: 20px; font-weight: 600; fill: #f3f4f6; animation: slideIn 0.5s ease-out; }}
    .count {{ font-family: system-ui, -apple-system, sans-serif; font-size: 40px; font-weight: 700; fill: #8b5cf6; animation: countUp 1s ease-out; }}
    .stat-label {{ font-family: system-ui, -apple-system, sans-serif; font-size: 12px; fill: #9ca3af; }}
    .stat-value {{ font-family: system-ui, -apple-system, sans-serif; font-size: 14px; fill: #f3f4f6; font-weight: 600; }}
    .tag {{ font-family: system-ui, -apple-system, sans-serif; font-size: 13px; fill: #6b7280; }}
    .line {{ stroke: #6b7280; stroke-width: 1; stroke-dasharray: 2 2; }}
    .bar-label {{ font-family: system-ui, -apple-system, sans-serif; font-size: 10px; fill: #9ca3af; text-anchor: middle; }}
    .circle-pulse {{ fill: #8b5cf6; animation: pulse 2s infinite; }}
  </style>
  
  <!-- Background -->
  <rect width="500" height="160" class="bg"/>
  <rect x="15" y="15" width="470" height="130" class="card"/>
  
  <!-- Header -->
  <text x="35" y="45" class="title">{svg_text}</text>
  <text x="35" y="65" class="tag">{tag}</text>
  
  <!-- Main count -->
  <text x="35" y="105" class="count">{formatted_views}</text>
  
  <!-- Divider -->
  <line x1="250" y1="35" x2="250" y2="125" class="line" />
  
  <!-- Stats -->
  <text x="35" y="130" class="stat-label">Daily Average:</text>
  <text x="120" y="130" class="stat-value">{stats['avg_daily']}</text>
  <text x="160" y="130" class="stat-label">Peak:</text>
  <text x="195" y="130" class="stat-value">{stats['peak_views']}</text>
  
  <!-- Pulse indicator -->
  <circle cx="220" cy="126" r="3" class="circle-pulse" />
  
  <!-- Bar chart title -->
  <text x="270" y="45" class="stat-label">LAST 7 DAYS</text>
  
  <!-- Bar chart -->
  <line x1="270" y1="100" x2="465" y2="100" stroke="#374151" stroke-width="1" />
  {"".join(bar_elements)}
  
  <!-- Footer -->
  <text x="465" y="130" class="stat-label" text-anchor="end">Updated: {datetime.datetime.now().strftime('%b %d')}</text>
</svg>'''

    return Response(svg, mimetype='image/svg+xml')

@app.route('/svg//count/3/<path:svg_text>/<tag>')
def generate_svg3(svg_text, tag):
    # Clean and decode tag
    tag = unquote(tag)
    
    # Update view count
    update_view_count(tag)
    
    # Get stats
    stats = get_repo_stats(tag)
    formatted_views = f"{stats['total_views']:,}"
    
    # Decode svg_text for display
    svg_text = unquote(svg_text)
    
    # Get daily data for the past 14 days for the circular view chart
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=14)
    
    query = {
        "tag": tag,
        "date": {"$gte": start_date, "$lte": end_date}
    }
    
    daily_data = list(views_collection.find(query).sort("date", 1))
    
    # If no data, create sample data
    if not daily_data:
        daily_data = [
            {"date": end_date - datetime.timedelta(days=i), 
             "views": int(stats["avg_daily"] * (0.7 + 0.6 * (i % 3) / 2))} 
            for i in range(14)
        ]
    
    # Create circular visualization
    center_x, center_y = 400, 80
    inner_radius, outer_radius = 40, 70
    
    circle_elements = []
    
    # Get max views for scaling
    max_views = max([d["views"] for d in daily_data]) if daily_data else 100
    
    for i, day_data in enumerate(daily_data):
        # Calculate angle (in radians)
        angle = 2 * 3.14159 * i / 14
        
        # Calculate height based on views (scaled)
        height_factor = day_data["views"] / max_views if max_views > 0 else 0.5
        bar_height = inner_radius + (outer_radius - inner_radius) * height_factor
        
        # Calculate positions
        x1 = center_x + inner_radius * math.cos(angle)
        y1 = center_y + inner_radius * math.sin(angle)
        x2 = center_x + bar_height * math.cos(angle)
        y2 = center_y + bar_height * math.sin(angle)
        
        # Create gradient ID
        gradient_id = f"radialGradient{i}"
        
        # Determine color based on height (higher = more intense)
        intensity = int(190 + 65 * height_factor)
        hue = int(200 + 40 * height_factor)
        
        # Add to elements
        circle_elements.append(f'''
    <linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="hsl({hue}, 80%, 65%)" />
      <stop offset="100%" stop-color="hsl({hue-30}, 90%, 45%)" />
    </linearGradient>
    <line 
      x1="{x1}" y1="{y1}" 
      x2="{x2}" y2="{y2}" 
      stroke="url(#{gradient_id})" 
      stroke-width="6" 
      stroke-linecap="round">
      <animate attributeName="x2" from="{x1}" to="{x2}" dur="1.2s" begin="{i * 0.1}s" fill="freeze" calcMode="elastic" />
      <animate attributeName="y2" from="{y1}" to="{y2}" dur="1.2s" begin="{i * 0.1}s" fill="freeze" calcMode="elastic" />
    </line>
    ''')
    
    # Get weekday name
    today = datetime.datetime.now()
    weekday = today.strftime("%A")
    
    # Generate SVG with minimalist design
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="160" viewBox="0 0 500 160" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
    <linearGradient id="titleGradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#9333ea" />
      <stop offset="100%" stop-color="#3b82f6" />
    </linearGradient>
  </defs>
  
  <style>
    @keyframes pulse {{ 0% {{ opacity: 0.7; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.7; }} }}
    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes countUp {{ 
      0% {{ transform: scale(0.8); opacity: 0; }} 
      70% {{ transform: scale(1.1); }}
      100% {{ transform: scale(1); opacity: 1; }}
    }}
    
    .container {{ fill: #ffffff; rx: 16; ry: 16; filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.08)); }}
    .title {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 22px; font-weight: 700; fill: url(#titleGradient); animation: fadeIn 1s ease-out; }}
    .count {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 46px; font-weight: 800; fill: #1e293b; animation: countUp 1.5s ease-out; }}
    .label {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 14px; fill: #64748b; }}
    .stat-value {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 16px; fill: #1e293b; font-weight: 600; }}
    .tag {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 14px; fill: #94a3b8; }}
    .circle-bg {{ fill: #f8fafc; stroke: #e2e8f0; stroke-width: 1; }}
    .today {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 12px; fill: #64748b; font-weight: 500; }}
    .center-dot {{ fill: #4f46e5; filter: url(#glow); animation: pulse 2s infinite; }}
  </style>
  
  <!-- Background -->
  <rect width="500" height="160" fill="#f1f5f9"/>
  <rect x="15" y="15" width="470" height="130" class="container"/>
  
  <!-- Title -->
  <text x="40" y="50" class="title">{svg_text}</text>
  <text x="40" y="75" class="tag">@{tag}</text>
  
  <!-- Main count with shadow -->
  <text x="40" y="120" class="count">{formatted_views}</text>
  
  <!-- Stats -->
  <text x="40" y="145" class="label">Daily avg: </text>
  <text x="110" y="145" class="stat-value">{stats['avg_daily']}</text>
  <text x="160" y="145" class="label">Peak: </text>
  <text x="200" y="145" class="stat-value">{stats['peak_views']}</text>
  
  <!-- Circle background -->
  <circle cx="{center_x}" cy="{center_y}" r="{outer_radius + 5}" class="circle-bg" />
  
  <!-- Circular chart -->
  {"".join(circle_elements)}
  
  <!-- Center dot and day -->
  <circle cx="{center_x}" cy="{center_y}" r="8" class="center-dot" />
  <text x="{center_x}" y="{center_y + outer_radius + 20}" class="today" text-anchor="middle">{weekday}</text>
</svg>'''

    return Response(svg, mimetype='image/svg+xml')



@app.route('/svg/count/4/<int:display_style>/<tag>')
def generate_count_svg(display_style, tag):
    # Clean and decode tag
    tag = unquote(tag)
    
    # Update view count
    update_view_count(tag)
    
    # Get stats
    stats = get_repo_stats(tag)
    total_views = stats['total_views']
    formatted_views = f"{total_views:,}"
    
    # Create digit animation
    # Break the count into individual digits
    digits = [int(d) for d in str(total_views)]
    
    # Define color themes based on style parameter
    themes = {
        1: {
            "bg": "#0f172a",
            "card": "#1e293b",
            "text": "#f8fafc",
            "accent": "#22d3ee",
            "font": "monospace"
        },
        2: {
            "bg": "#18181b",
            "card": "#27272a",
            "text": "#fafafa",
            "accent": "#a855f7",
            "font": "system-ui, -apple-system, sans-serif"
        },
        3: {
            "bg": "#0c0a09",
            "card": "#1c1917",
            "text": "#f5f5f4",
            "accent": "#f97316",
            "font": "Menlo, Monaco, monospace"
        },
        4: {
            "bg": "#022c22", 
            "card": "#134e4a",
            "text": "#f0fdfa",
            "accent": "#10b981",
            "font": "Helvetica, Arial, sans-serif"
        }
    }
    
    # Default to style 4 if not in range
    if display_style not in themes:
        display_style = 4
        
    theme = themes[display_style]
    
    # Generate the digits with animation
    digit_width = 28
    digit_spacing = 5
    start_x = 50
    
    # Generate SVG
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="300" height="100" viewBox="0 0 300 100" xmlns="http://www.w3.org/2000/svg">
  <style>
    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes flipDigit {{ 
      0% {{ transform: rotateX(90deg); opacity: 0; }} 
      100% {{ transform: rotateX(0deg); opacity: 1; }}
    }}
    @keyframes pulseGlow {{
      0% {{ filter: drop-shadow(0 0 3px {theme["accent"]}40); }}
      50% {{ filter: drop-shadow(0 0 6px {theme["accent"]}90); }}
      100% {{ filter: drop-shadow(0 0 3px {theme["accent"]}40); }}
    }}
    @keyframes borderPulse {{
      0% {{ stroke-opacity: 0.3; }}
      50% {{ stroke-opacity: 0.8; }}
      100% {{ stroke-opacity: 0.3; }}
    }}
    @keyframes float {{
      0% {{ transform: translateY(0px); }}
      50% {{ transform: translateY(-5px); }}
      100% {{ transform: translateY(0px); }}
    }}
    
    .bg {{ fill: {theme["bg"]}; }}
    .card {{ fill: {theme["card"]}; rx: 12; ry: 12; stroke: {theme["accent"]}; stroke-width: 1.5; stroke-opacity: 0.5; animation: borderPulse 3s infinite; }}
    .title {{ font-family: {theme["font"]}; font-size: 16px; font-weight: 600; fill: {theme["text"]}; }}
    .digit {{ font-family: {theme["font"]}; font-size: 38px; font-weight: 700; fill: {theme["accent"]}; }}
    .digit-bg {{ fill: {theme["card"]}; rx: 6; ry: 6; stroke: {theme["accent"]}30; stroke-width: 1; }}
    .tag {{ font-family: {theme["font"]}; font-size: 12px; fill: {theme["text"]}80; animation: fadeIn 1s ease-out; }}
    .icon {{ fill: none; stroke: {theme["accent"]}; stroke-width: 1.5; animation: pulseGlow 3s infinite; }}
  </style>
  
  <!-- Background -->
  <rect width="300" height="100" class="bg"/>
  <rect x="10" y="10" width="280" height="80" class="card"/>
  
  <!-- Title -->
  <text x="25" y="30" class="title">Repository Views</text>
  <text x="270" y="30" class="tag" text-anchor="end">{tag}</text>
  
  <!-- Counter digits -->
'''

    # Add each digit with animation
    for i, digit in enumerate(digits):
        x_pos = start_x + i * (digit_width + digit_spacing)
        delay = i * 0.15
        
        # Add digit background and the actual digit with animations
        svg += f'''
  <g style="animation: float 3s ease-in-out infinite {delay}s;">
    <rect x="{x_pos}" y="40" width="{digit_width}" height="40" class="digit-bg"/>
    <text x="{x_pos + digit_width/2}" y="70" class="digit" text-anchor="middle" style="animation: flipDigit 0.5s ease-out {delay}s both;">{digit}</text>
  </g>'''
    
    # Add icon and close SVG
    svg += f'''
  <!-- Icon -->
  <g transform="translate(240, 68)" class="icon">
    <path d="M12,10 L12,14 M16,12 L20,12 M4,12 L8,12 M10,6 L14,6 M12,4 L12,8" stroke-linecap="round"/>
    <circle cx="12" cy="12" r="10"/>
  </g>
</svg>'''

    return Response(svg, mimetype='image/svg+xml')


@app.route('/svg/count/5/<path:svg_text>/<tag>')
def generate_universe_svg(svg_text, tag):
    # Clean and decode tag
    tag = unquote(tag)
    
    # Update view count
    update_view_count(tag)
    
    # Get stats
    stats = get_repo_stats(tag)
    formatted_views = f"{stats['total_views']:,}"
    
    # Decode svg_text for display
    svg_text = unquote(svg_text)
    
    # Get data for the star field
    star_elements = []
    for i in range(80):  # Create 80 stars
        # Random positions
        x = random.randint(20, 480)
        y = random.randint(20, 140)
        
        # Random size (radius)
        size = random.uniform(0.3, 1.8)
        
        # Random opacity
        opacity = random.uniform(0.4, 1.0)
        
        # Random animation delay
        delay = random.uniform(0, 4)
        
        # Add star
        star_elements.append(f'''
    <circle cx="{x}" cy="{y}" r="{size}" fill="white" opacity="{opacity}">
      <animate attributeName="opacity" values="{opacity};{opacity*1.5};{opacity}" dur="{random.uniform(2, 5)}s" 
               repeatCount="indefinite" begin="{delay}s"/>
    </circle>''')
    
    # Create nebula elements
    nebula_elements = []
    for i in range(3):
        x = random.randint(200, 450)
        y = random.randint(30, 120)
        radius = random.randint(20, 50)
        
        # Generate random hue in purple/blue space
        hue = random.randint(220, 290)
        
        nebula_elements.append(f'''
    <radialGradient id="nebula{i}" cx="0.5" cy="0.5" r="0.5" fx="0.5" fy="0.5">
      <stop offset="0%" stop-color="hsl({hue}, 100%, 70%)" stop-opacity="0.7"/>
      <stop offset="100%" stop-color="hsl({hue}, 100%, 70%)" stop-opacity="0"/>
    </radialGradient>
    <circle cx="{x}" cy="{y}" r="{radius}" fill="url(#nebula{i})">
      <animate attributeName="r" values="{radius};{radius*1.1};{radius}" dur="{random.uniform(10, 15)}s" 
               repeatCount="indefinite"/>
    </circle>''')
    
    # Create planet
    planet_x = 70
    planet_y = 80
    planet_radius = 25
    
    # Generate the views as a digital counter with a cosmic theme
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="160" viewBox="0 0 500 160" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="cosmicBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f0326"/>
      <stop offset="50%" stop-color="#1a0533"/>
      <stop offset="100%" stop-color="#10012c"/>
    </linearGradient>
    
    <radialGradient id="planet" cx="0.5" cy="0.5" r="0.5" fx="0.4" fy="0.4">
      <stop offset="0%" stop-color="#7b3fe4"/>
      <stop offset="90%" stop-color="#2a0f6d"/>
    </radialGradient>
    
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5" fx="0.5" fy="0.5">
      <stop offset="0%" stop-color="#8a4fff" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#8a4fff" stop-opacity="0"/>
    </radialGradient>
    
    <filter id="cosmicGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur"/>
      <feComposite in="blur" in2="SourceGraphic" operator="over"/>
    </filter>
    
    <filter id="textGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>
  
  <style>
    @keyframes pulse {{ 
      0% {{ opacity: 0.7; transform: scale(1); }} 
      50% {{ opacity: 1; transform: scale(1.05); }} 
      100% {{ opacity: 0.7; transform: scale(1); }}
    }}
    @keyframes float {{ 
      0% {{ transform: translateY(0px) rotate(0deg); }} 
      50% {{ transform: translateY(-5px) rotate(1deg); }} 
      100% {{ transform: translateY(0px) rotate(0deg); }}
    }}
    @keyframes orbit {{ 
      0% {{ transform: rotate(0deg) translateX(10px) rotate(0deg); }} 
      100% {{ transform: rotate(360deg) translateX(10px) rotate(-360deg); }}
    }}
    @keyframes countUp {{ 
      0% {{ transform: translateY(20px); opacity: 0; }} 
      100% {{ transform: translateY(0); opacity: 1; }}
    }}
    
    .bg {{ fill: url(#cosmicBg); }}
    .title {{ font-family: "Space Grotesk", system-ui, sans-serif; font-size: 22px; font-weight: 700; fill: white; filter: url(#textGlow); }}
    .count {{ font-family: "Space Grotesk", system-ui, sans-serif; font-size: 42px; font-weight: 800; fill: white; filter: url(#textGlow); animation: countUp 1.5s ease-out; }}
    .subtitle {{ font-family: "Space Grotesk", system-ui, sans-serif; font-size: 14px; fill: #9d9efa; }}
    .stat-value {{ font-family: "Space Grotesk", system-ui, sans-serif; font-size: 16px; fill: white; }}
    .planet {{ fill: url(#planet); filter: url(#cosmicGlow); animation: pulse 10s infinite; }}
    .orbit {{ fill: none; stroke: rgba(255, 255, 255, 0.2); stroke-dasharray: 3 3; }}
    .moon {{ fill: #b19fff; filter: url(#cosmicGlow); animation: orbit 20s linear infinite; }}
    .ring {{ fill: none; stroke: #b19fff; stroke-opacity: 0.6; }}
    .glow-circle {{ fill: url(#glow); animation: pulse 8s infinite; }}
  </style>
  
  <!-- Background -->
  <rect width="500" height="160" class="bg"/>
  
  <!-- Stars -->
  {"".join(star_elements)}
  
  <!-- Nebulae -->
  {"".join(nebula_elements)}
  
  <!-- Planet -->
  <circle cx="{planet_x}" cy="{planet_y}" r="{planet_radius}" class="planet"/>
  <circle cx="{planet_x}" cy="{planet_y}" r="{planet_radius + 15}" fill="url(#glow)" class="glow-circle"/>
  
  <!-- Rings -->
  <ellipse cx="{planet_x}" cy="{planet_y}" rx="{planet_radius + 10}" ry="{(planet_radius + 10) * 0.3}" class="ring" 
           transform="rotate(-15, {planet_x}, {planet_y})"/>
  <ellipse cx="{planet_x}" cy="{planet_y}" rx="{planet_radius + 15}" ry="{(planet_radius + 15) * 0.3}" class="ring" 
           transform="rotate(-15, {planet_x}, {planet_y})"/>
  
  <!-- Title -->
  <text x="150" y="50" class="title">{svg_text}</text>
  <text x="150" y="72" class="subtitle">Repository: {tag}</text>
  
  <!-- Main count with glow -->
  <text x="150" y="115" class="count">{formatted_views}</text>
  
  <!-- Stats -->
  <text x="150" y="140" class="subtitle">Daily average: </text>
  <text x="250" y="140" class="stat-value">{stats['avg_daily']}</text>
  <text x="300" y="140" class="subtitle">Peak: </text>
  <text x="340" y="140" class="stat-value">{stats['peak_views']}</text>
  
  <!-- Moon/satellite orbiting -->
  <circle cx="{planet_x}" cy="{planet_y-8}" r="3" class="moon"/>
</svg>'''

    return Response(svg, mimetype='image/svg+xml')



@app.route('/svg/count/6/<path:svg_text>/<tag>')
def generate_blackhole_svg(svg_text, tag):
    # Clean and decode tag
    tag = unquote(tag)
    
    # Update view count
    update_view_count(tag)
    
    # Get stats
    stats = get_repo_stats(tag)
    formatted_views = f"{stats['total_views']:,}"
    
    # Decode svg_text for display
    svg_text = unquote(svg_text)
    
    # Create background stars
    star_elements = []
    for i in range(120):  # Create 120 stars
        # Random positions
        x = random.randint(20, 480)
        y = random.randint(20, 140)
        
        # Random size (radius)
        size = random.uniform(0.2, 1.5)
        
        # Random opacity
        opacity = random.uniform(0.2, 0.9)
        
        # Random animation delay
        delay = random.uniform(0, 5)
        
        # Add star
        star_elements.append(f'''
    <circle cx="{x}" cy="{y}" r="{size}" fill="white" opacity="{opacity}">
      <animate attributeName="opacity" values="{opacity};{opacity*1.8};{opacity}" dur="{random.uniform(2, 6)}s" 
               repeatCount="indefinite" begin="{delay}s"/>
    </circle>''')
    
    # Create accretion disk elements
    accretion_elements = []
    blackhole_x = 400
    blackhole_y = 80
    blackhole_radius = 25
    
    # Create multiple rings for the accretion disk
    for i in range(5):
        radius = blackhole_radius + 5 + (i * 6)
        opacity = 0.9 - (i * 0.15)
        hue = 30 + (i * 20)  # Orange to yellow-white gradient
        
        accretion_elements.append(f'''
    <ellipse cx="{blackhole_x}" cy="{blackhole_y}" rx="{radius}" ry="{radius * 0.3}" 
             fill="none" stroke="hsl({hue}, 100%, {60 + i * 8}%)" stroke-width="{3 - i * 0.4}" stroke-opacity="{opacity}"
             transform="rotate({i*5}, {blackhole_x}, {blackhole_y})">
        <animateTransform attributeName="transform" type="rotate" 
                          from="{i*5} {blackhole_x} {blackhole_y}" 
                          to="{i*5 + 360} {blackhole_x} {blackhole_y}" 
                          dur="{25 - i*3}s" repeatCount="indefinite"/>
    </ellipse>''')
    
    # Light distortion effect around black hole
    light_distortion = []
    for i in range(12):
        angle = i * 30
        length = random.uniform(5, 20)
        width = random.uniform(1, 3)
        
        # Convert angle to radians
        rad = math.radians(angle)
        
        # Calculate end point
        end_x = blackhole_x + length * math.cos(rad)
        end_y = blackhole_y + length * math.sin(rad)
        
        light_distortion.append(f'''
    <line x1="{blackhole_x}" y1="{blackhole_y}" x2="{end_x}" y2="{end_y}" 
          stroke="white" stroke-width="{width}" stroke-opacity="0.6" stroke-linecap="round">
        <animate attributeName="stroke-opacity" values="0.2;0.6;0.2" dur="{random.uniform(2, 4)}s" 
                 repeatCount="indefinite" begin="{random.uniform(0, 2)}s"/>
    </line>''')
    
    # Generate view count digits with gravitational animation
    digits = str(stats['total_views'])
    digit_elements = []
    
    for i, digit in enumerate(digits):
        # Position digits in arc around black hole
        angle = 180 - (i * (140 / (len(digits) - 1 if len(digits) > 1 else 1)))
        radius = 100
        
        # Convert angle to radians
        rad = math.radians(angle)
        
        # Calculate position
        x = blackhole_x + radius * math.cos(rad)
        y = blackhole_y + radius * math.sin(rad)
        
        # Create "gravitational pull" animation toward black hole
        pull_x = x + (blackhole_x - x) * 0.15
        pull_y = y + (blackhole_y - y) * 0.15
        
        digit_elements.append(f'''
    <text x="{x}" y="{y}" class="digit" text-anchor="middle" dominant-baseline="middle">
        {digit}
        <animate attributeName="x" values="{x};{pull_x};{x}" dur="{4 + i*0.2}s" begin="{i*0.1}s" repeatCount="indefinite"/>
        <animate attributeName="y" values="{y};{pull_y};{y}" dur="{4 + i*0.2}s" begin="{i*0.1}s" repeatCount="indefinite"/>
        <animate attributeName="font-size" values="28;30;28" dur="{4 + i*0.2}s" begin="{i*0.1}s" repeatCount="indefinite"/>
    </text>''')
    
    # Generate the SVG with black hole theme
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="160" viewBox="0 0 500 160" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="blackholeBg" cx="0.5" cy="0.5" r="0.8" fx="0.5" fy="0.5">
      <stop offset="0%" stop-color="#000510"/>
      <stop offset="100%" stop-color="#00020a"/>
    </radialGradient>
    
    <radialGradient id="blackholeGradient" cx="0.5" cy="0.5" r="0.5" fx="0.5" fy="0.5">
      <stop offset="0%" stop-color="#000000"/>
      <stop offset="75%" stop-color="#000000"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0"/>
    </radialGradient>
    
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur"/>
      <feComposite in="blur" in2="SourceGraphic" operator="over"/>
    </filter>
    
    <filter id="distortion" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="1" seed="1" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="5" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    
    <linearGradient id="titleGradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ff6b00"/>
      <stop offset="100%" stop-color="#ff9d00"/>
    </linearGradient>
  </defs>
  
  <style>
    @keyframes pulse {{ 
      0% {{ opacity: 0.7; }} 
      50% {{ opacity: 1; }} 
      100% {{ opacity: 0.7; }}
    }}
    @keyframes spin {{ 
      0% {{ transform: rotate(0deg); }} 
      100% {{ transform: rotate(360deg); }}
    }}
    @keyframes expand {{ 
      0% {{ transform: scale(1); }} 
      50% {{ transform: scale(1.1); }} 
      100% {{ transform: scale(1); }}
    }}
    
    .bg {{ fill: url(#blackholeBg); }}
    .title {{ font-family: "Orbitron", "Space Grotesk", system-ui, sans-serif; font-size: 20px; font-weight: 700; fill: url(#titleGradient); filter: url(#glow); }}
    .subtitle {{ font-family: "Orbitron", "Space Grotesk", system-ui, sans-serif; font-size: 12px; fill: #b38d42; }}
    .digit {{ font-family: "Orbitron", "Space Grotesk", system-ui, sans-serif; font-size: 28px; font-weight: 700; fill: white; filter: url(#glow); }}
    .stat-label {{ font-family: "Orbitron", "Space Grotesk", system-ui, sans-serif; font-size: 12px; fill: #8f8f8f; }}
    .stat-value {{ font-family: "Orbitron", "Space Grotesk", system-ui, sans-serif; font-size: 14px; fill: #ffa726; }}
    .blackhole {{ fill: url(#blackholeGradient); }}
    .blackhole-core {{ fill: black; }}
    .blackhole-event-horizon {{ fill: none; stroke: #ff9800; stroke-width: 0.5; stroke-opacity: 0.2; animation: pulse 4s infinite; }}
  </style>
  
  <!-- Background -->
  <rect width="500" height="160" class="bg"/>
  
  <!-- Stars -->
  {"".join(star_elements)}
  
  <!-- Accretion disk -->
  {"".join(accretion_elements)}
  
  <!-- Light distortion effects -->
  {"".join(light_distortion)}
  
  <!-- Black hole -->
  <circle cx="{blackhole_x}" cy="{blackhole_y}" r="{blackhole_radius + 3}" class="blackhole" filter="url(#distortion)"/>
  <circle cx="{blackhole_x}" cy="{blackhole_y}" r="{blackhole_radius}" class="blackhole-core"/>
  <circle cx="{blackhole_x}" cy="{blackhole_y}" r="{blackhole_radius}" class="blackhole-event-horizon">
    <animate attributeName="r" values="{blackhole_radius};{blackhole_radius + 5};{blackhole_radius}" dur="3s" repeatCount="indefinite"/>
  </circle>
  
  <!-- Title -->
  <text x="40" y="50" class="title">{svg_text}</text>
  <text x="40" y="70" class="subtitle">REPOSITORY: {tag}</text>
  
  <!-- Stats -->
  <text x="40" y="120" class="stat-label">DAILY AVERAGE:</text>
  <text x="140" y="120" class="stat-value">{stats['avg_daily']}</text>
  <text x="40" y="140" class="stat-label">PEAK VIEWS:</text>
  <text x="115" y="140" class="stat-value">{stats['peak_views']}</text>
  
  <!-- Orbit indicator -->
  <circle cx="{blackhole_x + 60}" cy="{blackhole_y - 30}" r="2" fill="orange" opacity="0.8">
    <animate attributeName="cx" values="{blackhole_x + 60};{blackhole_x + 55};{blackhole_x + 40};{blackhole_x + 55};{blackhole_x + 60}" 
             dur="8s" repeatCount="indefinite"/>
    <animate attributeName="cy" values="{blackhole_y - 30};{blackhole_y - 20};{blackhole_y - 10};{blackhole_y - 20};{blackhole_y - 30}" 
             dur="8s" repeatCount="indefinite"/>
  </circle>
  
  <!-- Digits affected by gravity -->
  {"".join(digit_elements)}
</svg>'''

    return Response(svg, mimetype='image/svg+xml')

@app.route('/svg/count/7/<path:svg_text>/<tag>')
def generate_blackhole_svg2(svg_text, tag):
    # Clean and decode tag
    tag = unquote(tag)
    
    # Update view count
    update_view_count(tag)
    
    # Get stats
    stats = get_repo_stats(tag)
    formatted_views = f"{stats['total_views']:,}"
    
    # Decode svg_text for display
    svg_text = unquote(svg_text)
    
    # Create star elements (background stars)
    star_elements = []
    for i in range(120):  # More stars for deeper space feel
        # Random positions
        x = random.randint(10, 490)
        y = random.randint(10, 150)
        
        # Random size (radius)
        size = random.uniform(0.2, 1.5)
        
        # Distance from center (for determining brightness)
        dx = x - 250  # Center x
        dy = y - 80   # Center y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Stars closer to black hole are dimmer
        base_opacity = max(0.2, min(0.9, distance / 250))
        
        # Random animation delay
        delay = random.uniform(0, 5)
        
        # Add star with pulsing animation
        star_elements.append(f'''
    <circle cx="{x}" cy="{y}" r="{size}" fill="white" opacity="{base_opacity}">
      <animate attributeName="opacity" 
               values="{base_opacity};{base_opacity*0.4};{base_opacity}" 
               dur="{random.uniform(2, 8)}s" 
               repeatCount="indefinite" 
               begin="{delay}s"/>
    </circle>''')
    
    # Create accretion disk particles
    accretion_particles = []
    center_x, center_y = 250, 80
    


    # Parameters for the accretion disk
    num_particles = 180
    min_radius = 40
    max_radius = 90
    
    for i in range(num_particles):
        # Calculate angle
        angle = random.uniform(0, 2 * math.pi)
        
        # Calculate radius (more particles towards outer edge)
        radius_factor = random.uniform(0, 1) ** 0.5  # Square root for distribution
        radius = min_radius + (max_radius - min_radius) * radius_factor
        
        # Calculate position
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        
        # Particle properties based on distance
        particle_size = random.uniform(0.5, 2.0)
        
        # Color based on temperature (inner is hotter)
        temp_factor = 1 - (radius - min_radius) / (max_radius - min_radius)
        hue = int(220 * temp_factor)  # 220 (blue) to 0 (red)
        saturation = 80 + int(20 * temp_factor)
        lightness = 50 + int(30 * temp_factor)
        
        # Orbital speed (inner particles move faster)
        orbital_period = 8 + (30 * (radius - min_radius) / (max_radius - min_radius))
        
        # Add particle
        accretion_particles.append(f'''
    <circle cx="{x}" cy="{y}" r="{particle_size}" fill="hsl({hue}, {saturation}%, {lightness}%)">
      <animateTransform 
        attributeName="transform" 
        type="rotate" 
        from="{angle * 180 / math.pi} {center_x} {center_y}" 
        to="{angle * 180 / math.pi + 360} {center_x} {center_y}" 
        dur="{orbital_period}s" 
        repeatCount="indefinite"/>
      <animate 
        attributeName="opacity" 
        values="0.4;0.9;0.4" 
        dur="{random.uniform(2, 4)}s" 
        repeatCount="indefinite"/>
    </circle>''')
    
    # Create the black hole event horizon with relativistic effects
    black_hole_radius = 25
    
    # Generate SVG with black hole theme
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="160" viewBox="0 0 500 160" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <defs>
    <!-- Deep space background -->
    <linearGradient id="spaceBackground" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0a0f"/>
      <stop offset="50%" stop-color="#151530"/>
      <stop offset="100%" stop-color="#0a0a1a"/>
    </linearGradient>
    
    <!-- Black hole gravitational lensing effect -->
    <radialGradient id="eventHorizon" cx="0.5" cy="0.5" r="0.5" fx="0.5" fy="0.5">
      <stop offset="0%" stop-color="black"/>
      <stop offset="85%" stop-color="black"/>
      <stop offset="95%" stop-color="#5000ff" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="black" stop-opacity="0.5"/>
    </radialGradient>
    
    <!-- Accretion disk glow -->
    <radialGradient id="diskGlow" cx="0.5" cy="0.5" r="0.5" fx="0.5" fy="0.5">
      <stop offset="0%" stop-color="#8a4fff" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#0000ff" stop-opacity="0"/>
    </radialGradient>
    
    <!-- Text effects -->
    <filter id="textGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    
    <!-- Animation path for particles being sucked in -->
    <path id="suckPath" d="M300,80 Q275,80 250,80">
      <animate attributeName="d" 
               values="M300,80 Q275,80 250,80; M290,75 Q270,77 250,80; M300,80 Q275,80 250,80" 
               dur="3s" 
               repeatCount="indefinite"/>
    </path>
  </defs>
  
  <style>
    @keyframes gravitational-pull {{
      0% {{ transform: scale(1) translate(0, 0); }}
      50% {{ transform: scale(0.98) translate(2px, 1px); }}
      100% {{ transform: scale(1) translate(0, 0); }}
    }}
    @keyframes flicker {{
      0% {{ opacity: 0.8; }}
      25% {{ opacity: 1; }}
      50% {{ opacity: 0.6; }}
      75% {{ opacity: 0.9; }}
      100% {{ opacity: 0.8; }}
    }}
    @keyframes rotating {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}
    @keyframes countUp {{
      0% {{ opacity: 0; transform: scale(0.8); filter: blur(5px); }}
      50% {{ opacity: 0.5; transform: scale(1.05); filter: blur(2px); }}
      100% {{ opacity: 1; transform: scale(1); filter: blur(0); }}
    }}
    
    .bg {{ fill: url(#spaceBackground); }}
    .title {{ font-family: "Exo 2", system-ui, sans-serif; font-size: 22px; font-weight: 700; fill: white; filter: url(#textGlow); }}
    .count {{ 
      font-family: "Exo 2", system-ui, sans-serif; 
      font-size: 42px; 
      font-weight: 800; 
      fill: white; 
      filter: url(#textGlow); 
      animation: countUp 1.8s ease-out forwards;
    }}
    .subtitle {{ font-family: "Exo 2", system-ui, sans-serif; font-size: 14px; fill: #8b8bff; }}
    .stat-value {{ font-family: "Exo 2", system-ui, sans-serif; font-size: 16px; fill: white; }}
    .black-hole {{ fill: url(#eventHorizon); animation: flicker 4s infinite ease-in-out; }}
    .distortion-ring {{ 
      fill: none; 
      stroke: rgba(140, 100, 255, 0.15); 
      stroke-width: 3;
      animation: gravitational-pull 5s infinite ease-in-out; 
    }}
    .glow-effect {{ fill: url(#diskGlow); animation: rotating 20s linear infinite; transform-origin: 250px 80px; }}
  </style>
  
  <!-- Background -->
  <rect width="500" height="160" class="bg"/>
  
  <!-- Background stars -->
  {"".join(star_elements)}
  
  <!-- Gravitational distortion rings -->
  <circle cx="250" cy="80" r="105" class="distortion-ring" opacity="0.3"/>
  <circle cx="250" cy="80" r="85" class="distortion-ring" opacity="0.4"/>
  <circle cx="250" cy="80" r="65" class="distortion-ring" opacity="0.5"/>
  
  <!-- Black hole glow effect -->
  <ellipse cx="250" cy="80" rx="120" ry="60" class="glow-effect"/>
  
  <!-- Accretion disk particles -->
  {"".join(accretion_particles)}
  
  <!-- Black hole event horizon -->
  <circle cx="250" cy="80" r="{black_hole_radius}" class="black-hole">
    <animate attributeName="r" 
             values="{black_hole_radius};{black_hole_radius-1};{black_hole_radius+2};{black_hole_radius}" 
             dur="8s" 
             repeatCount="indefinite"/>
  </circle>
  
  <!-- Title and stats (positioned on the left) -->
  <g transform="translate(0, 0)">
    <text x="30" y="50" class="title">{svg_text}</text>
    <text x="30" y="72" class="subtitle">Repository: {tag}</text>
    
    <!-- Main count with glow effect -->
    <text x="30" y="115" class="count">{formatted_views}</text>
    
    <!-- Stats -->
    <text x="30" y="140" class="subtitle">Daily avg: </text>
    <text x="100" y="140" class="stat-value">{stats['avg_daily']}</text>
    <text x="150" y="140" class="subtitle">Peak: </text>
    <text x="190" y="140" class="stat-value">{stats['peak_views']}</text>
  </g>
  
  <!-- Simulating matter being sucked into the black hole -->
  <g>
    <animate attributeName="opacity" values="0;1;0" dur="4s" repeatCount="indefinite"/>
    <animateMotion path="M400,40 Q325,60 250,80" dur="2s" repeatCount="indefinite">
      <mpath xlink:href="#suckPath"/>
    </animateMotion>
    <circle r="1.5" fill="#ffffff"/>
  </g>
  <g>
    <animate attributeName="opacity" values="0;1;0" dur="5s" begin="1s" repeatCount="indefinite"/>
    <animateMotion path="M350,100 Q300,90 250,80" dur="3s" repeatCount="indefinite">
      <mpath xlink:href="#suckPath"/>
    </animateMotion>
    <circle r="1" fill="#aaaaff"/>
  </g>
  <g>
    <animate attributeName="opacity" values="0;1;0" dur="3s" begin="2s" repeatCount="indefinite"/>
    <animateMotion path="M390,80 Q320,80 250,80" dur="2.5s" repeatCount="indefinite">
      <mpath xlink:href="#suckPath"/>
    </animateMotion>
    <circle r="2" fill="#ffaaff"/>
  </g>
</svg>'''

    return Response(svg, mimetype='image/svg+xml')


@app.route('/svg/count/8/<path:svg_text>/<tag>')
def generate_blackhole_svg8(svg_text, tag):
    # Clean and decode tag
    tag = unquote(tag)
    
    # Update view count
    update_view_count(tag)
    
    # Get stats
    stats = get_repo_stats(tag)
    formatted_views = f"{stats['total_views']:,}"
    
    # Decode svg_text for display
    svg_text = unquote(svg_text)
    
    # Create accretion disk particles
    disk_particles = []
    blackhole_x, blackhole_y = 380, 80
    blackhole_radius = 30
    
    # Generate particles for the accretion disk
    for i in range(160):
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(blackhole_radius + 5, blackhole_radius + 35)
        
        # Apply elliptical transformation
        x = blackhole_x + distance * math.cos(angle) * 1.2
        y = blackhole_y + distance * math.sin(angle) * 0.6
        
        # Random size
        size = random.uniform(0.5, 1.5)
        
        # Color gradient based on distance (closer = hotter)
        normalized_distance = (distance - (blackhole_radius + 5)) / 30
        
        # Color gradient: close=white/blue, far=orange/red
        if normalized_distance < 0.3:
            color = f"hsl({random.randint(180, 220)}, 100%, {80 - normalized_distance * 100}%)"
        elif normalized_distance < 0.6:
            color = f"hsl({random.randint(180, 600)}, 100%, {70 - normalized_distance * 50}%)"
        else:
            color = f"hsl({random.randint(0, 30)}, 100%, {60 - normalized_distance * 20}%)"
            
        # Animation properties
        orbit_duration = random.uniform(8, 15)
        
        # Add particle with orbital animation
        disk_particles.append(f'''
    <circle cx="{x}" cy="{y}" r="{size}" fill="{color}">
      <animateTransform attributeName="transform" type="rotate" 
          from="0 {blackhole_x} {blackhole_y}" to="360 {blackhole_x} {blackhole_y}" 
          dur="{orbit_duration}s" repeatCount="indefinite" additive="sum"/>
    </circle>''')
    
    # Create background stars
    star_elements = []
    for i in range(60):
        x = random.randint(20, 480)
        y = random.randint(20, 140)
        
        # Skip stars that are too close to the black hole
        if abs(x - blackhole_x) < 100 and abs(y - blackhole_y) < 60:
            continue
            
        size = random.uniform(0.3, 1.2)
        opacity = random.uniform(0.4, 0.9)
        
        star_elements.append(f'''
    <circle cx="{x}" cy="{y}" r="{size}" fill="white" opacity="{opacity}"/>''')
    
    # Create text animation (being pulled into black hole)
    text_animation = f'''
    <animateTransform attributeName="transform" type="rotate" 
        from="0 {blackhole_x} {blackhole_y}" to="360 {blackhole_x} {blackhole_y}" 
        dur="30s" repeatCount="indefinite" additive="sum"/>
    '''
    
    # Generate SVG
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="160" viewBox="0 0 500 160" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="spaceGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#000000"/>
      <stop offset="50%" stop-color="#050123"/>
      <stop offset="100%" stop-color="#000000"/>
    </linearGradient>
    
    <radialGradient id="eventHorizon" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="#000000"/>
      <stop offset="40%" stop-color="#000000"/>
      <stop offset="100%" stop-color="#000033"/>
    </radialGradient>
    
    <radialGradient id="gravitationalLens" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="rgba(0,0,0,0)"/>
      <stop offset="85%" stop-color="rgba(0,0,0,0)"/>
      <stop offset="100%" stop-color="rgba(100,200,255,0.2)"/>
    </radialGradient>
    
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    
    <filter id="distortion" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" result="turbulence"/>
      <feDisplacementMap in="SourceGraphic" in2="turbulence" scale="5" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    
    <!-- Text path that spirals toward the black hole -->
    <path id="spiralPath" d="M 150,90 Q 200,70 250,90 T 350,90" />
  </defs>
  
  <style>
    @keyframes pulse {{ 
      0% {{ opacity: 0.7; }} 
      50% {{ opacity: 1; }} 
      100% {{ opacity: 0.7; }}
    }}
    @keyframes warping {{
      0% {{ transform: scale(1) rotate(0deg); }}
      50% {{ transform: scale(1.05) rotate(0.5deg); }}
      100% {{ transform: scale(1) rotate(0deg); }}
    }}
    @keyframes gravitationalPull {{
      0% {{ transform: translateX(0); }}
      100% {{ transform: translateX(5px); }}
    }}
    @keyframes shine {{
      0% {{ opacity: 0.4; }}
      25% {{ opacity: 1; }}
      50% {{ opacity: 0.4; }}
      75% {{ opacity: 0.8; }}
      100% {{ opacity: 0.4; }}
    }}
    
    .bg {{ fill: url(#spaceGradient); }}
    .blackhole {{ fill: url(#eventHorizon); }}
    .lens {{ fill: url(#gravitationalLens); animation: warping 10s ease-in-out infinite; }}
    .title {{ font-family: "Orbitron", "Arial", sans-serif; font-size: 22px; font-weight: 700; fill: white; filter: url(#glow); }}
    .count {{ font-family: "Orbitron", "Arial", sans-serif; font-size: 40px; font-weight: 800; fill: white; }}
    .subtitle {{ font-family: "Orbitron", "Arial", sans-serif; font-size: 14px; fill: #7f9ccb; }}
    .stat-value {{ font-family: "Orbitron", "Arial", sans-serif; font-size: 16px; fill: white; }}
    .path-text {{ fill: white; font-family: "Orbitron", "Arial", sans-serif; font-size: 12px; animation: shine 4s infinite; }}
  </style>
  
  <!-- Background -->
  <rect width="500" height="160" class="bg"/>
  
  <!-- Background stars -->
  {"".join(star_elements)}
  
  <!-- Gravity lens effect (larger than the black hole) -->
  <circle cx="{blackhole_x}" cy="{blackhole_y}" r="{blackhole_radius * 3}" class="lens"/>
  
  <!-- Accretion disk particles -->
  {"".join(disk_particles)}
  
  <!-- Black hole -->
  <circle cx="{blackhole_x}" cy="{blackhole_y}" r="{blackhole_radius}" class="blackhole"/>
  
  <!-- Light being pulled in effect -->
  <path d="M 150,60 Q 200,60 {blackhole_x-blackhole_radius-20},{blackhole_y-10}" 
        stroke="rgba(255,255,255,0.3)" fill="none" stroke-width="1" stroke-dasharray="2 3">
    <animate attributeName="d" 
             from="M 150,60 Q 200,60 {blackhole_x-blackhole_radius-20},{blackhole_y-10}" 
             to="M 150,60 Q 220,60 {blackhole_x-blackhole_radius-5},{blackhole_y-5}" 
             dur="8s" repeatCount="indefinite" />
  </path>
  
  <!-- Title -->
  <text x="40" y="50" class="title">{svg_text}</text>
  <text x="40" y="70" class="subtitle">Repository: {tag}</text>
  
  <!-- Main count with spacetime distortion effect -->
  <text x="40" y="115" class="count" filter="url(#distortion)">{formatted_views}</text>
  
  <!-- Stats -->
  <text x="40" y="140" class="subtitle">Daily average: </text>
  <text x="140" y="140" class="stat-value">{stats['avg_daily']}</text>
  <text x="180" y="140" class="subtitle">Peak: </text>
  <text x="220" y="140" class="stat-value">{stats['peak_views']}</text>
  
  <!-- Text being pulled into black hole -->
  <text>
    <textPath href="#spiralPath" class="path-text">data streaming...{tag}...{stats['avg_daily']}...{stats['peak_views']}...
      {text_animation}
    </textPath>
  </text>
</svg>'''

    return Response(svg, mimetype='image/svg+xml')


@app.route('/svg/count/9/<path:svg_text>/<tag>')
def generate_hacker_svg9(svg_text, tag):
    # Clean and decode tag
    tag = unquote(tag)
    
    # Update view count
    update_view_count(tag)
    
    # Get stats
    stats = get_repo_stats(tag)
    total_views = stats['total_views']
    formatted_views = f"{total_views:,}"
    
    # Decode svg_text for display
    svg_text = unquote(svg_text)
    
    # Break the count into individual digits for the counter animation
    digits = [int(d) for d in str(total_views)]
    
    # Generate binary background
    binary_elements = []
    for i in range(200):
        x = random.randint(0, 500)
        y = random.randint(0, 160)
        binary_digit = random.choice(["0", "1"])
        opacity = random.uniform(0.1, 0.5)
        size = random.uniform(8, 12)
        
        # Animation delay
        delay = random.uniform(0, 10)
        duration = random.uniform(2, 5)
        
        binary_elements.append(f'''
    <text x="{x}" y="{y}" 
          font-family="'Courier New', monospace" font-size="{size}px" 
          fill="#00ff00" opacity="{opacity}">
      {binary_digit}
      <animate attributeName="opacity" 
               values="{opacity};{opacity*1.5};{opacity}" 
               dur="{duration}s" 
               repeatCount="indefinite" 
               begin="{delay}s"/>
    </text>''')
    
    # Create code lines (simulating terminal output)
    code_lines = []
    y_pos = 30
    code_snippets = [
        "Accessing repository metrics...",
        f"Repository: {tag}",
        "Retrieving view statistics...",
        "Processing data...",
        f"Average views: {stats['avg_daily']}/day",
        f"Peak traffic: {stats['peak_views']} views",
        "Status: Online"
    ]
    
    for i, line in enumerate(code_snippets):
        delay = i * 0.3
        y_pos += 12
        
        code_lines.append(f'''
    <text x="40" y="{y_pos}" 
          font-family="'Courier New', monospace" font-size="11px" 
          fill="#00ff00" opacity="0">
      {line}
      <animate attributeName="opacity" 
               values="0;1" 
               dur="0.3s" 
               begin="{delay}s" 
               fill="freeze"/>
    </text>''')
    
    # Create terminal cursor blink
    cursor_blink = f'''
    <rect x="40" y="{y_pos+5}" width="6" height="12" fill="#00ff00">
      <animate attributeName="opacity" 
               values="1;0;1" 
               dur="1s" 
               repeatCount="indefinite" 
               begin="{len(code_snippets) * 0.3 + 0.3}s"/>
    </rect>'''
    
    # Generate the matrix-like animation for the counter display
    counter_elements = []
    x_pos = 270
    
    for i, digit in enumerate(digits):
        delay = 2.0 + i * 0.2
        
        # Create scrambling animation
        scramble_values = []
        for j in range(10):
            scramble_values.append(random.randint(0, 9))
        scramble_values.append(digit)  # End with the correct digit
        
        value_list = ";".join(map(str, scramble_values))
        
        counter_elements.append(f'''
    <text x="{x_pos}" y="90" 
          font-family="'Courier New', monospace" font-size="40px" font-weight="bold" 
          fill="#00ff00" filter="url(#greenGlow)">
      0
      <animate attributeName="fill" 
               values="#00ff00;#ffffff;#00ff00" 
               dur="0.5s" 
               begin="{delay + 0.5}s" 
               fill="freeze"/>
      <animate attributeName="text-content" 
               values="{value_list}" 
               dur="0.5s" 
               begin="{delay}s" 
               fill="freeze"/>
    </text>''')
        
        x_pos += 24
    
    # Add glitch animation to the title
    glitch_title = f'''
    <text x="270" y="40" 
          font-family="'Courier New', monospace" font-size="18px" font-weight="bold" 
          fill="#00ff00" filter="url(#greenGlow)">
      {svg_text}
      <animate attributeName="x" 
               values="270;272;269;273;270" 
               dur="0.2s" 
               repeatCount="indefinite" 
               begin="3s"/>
      <animate attributeName="fill" 
               values="#00ff00;#ffffff;#00ff00" 
               dur="0.1s" 
               repeatCount="indefinite" 
               begin="3s"/>
    </text>'''
    
    # Create circuit board pattern
    circuit_elements = []
    
    # Horizontal lines
    for y in range(20, 160, 20):
        x_end = random.randint(400, 480)
        circuit_elements.append(f'''
    <path d="M 250,{y} H {x_end}" 
          stroke="#00ff00" stroke-width="1" opacity="0.3" fill="none" />''')
    
    # Vertical lines
    for x in range(270, 480, 30):
        y_end = random.randint(20, 140)
        circuit_elements.append(f'''
    <path d="M {x},{160} V {y_end}" 
          stroke="#00ff00" stroke-width="1" opacity="0.3" fill="none" />''')
    
    # Generate SVG
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="160" viewBox="0 0 500 160" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="greenGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    <filter id="scanline" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.01" numOctaves="1" result="noise"/>
      <feColorMatrix in="noise" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.05 0" result="colorNoise"/>
      <feComposite in="SourceGraphic" in2="colorNoise" operator="arithmetic" k1="0" k2="1" k3="1" k4="0"/>
    </filter>
    <mask id="terminalScreen">
      <rect width="200" height="130" x="30" y="15" fill="white" rx="5" ry="5"/>
    </mask>
    <linearGradient id="screenGlow" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#002200"/>
      <stop offset="100%" stop-color="#001100"/>
    </linearGradient>
  </defs>
  
  <style>
    @keyframes flicker {{
      0% {{ opacity: 0.95; }}
      5% {{ opacity: 0.85; }}
      10% {{ opacity: 0.97; }}
      15% {{ opacity: 0.88; }}
      20% {{ opacity: 0.9; }}
      70% {{ opacity: 1; }}
      80% {{ opacity: 0.85; }}
      100% {{ opacity: 0.95; }}
    }}
    @keyframes scan {{
      0% {{ transform: translateY(-100px); }}
      100% {{ transform: translateY(160px); }}
    }}
    
    .bg {{ fill: #000000; }}
    .terminal {{ fill: url(#screenGlow); rx: 5; ry: 5; stroke: #00ff00; stroke-width: 2; animation: flicker 4s infinite; }}
    .scanline {{ fill: rgba(0, 255, 0, 0.05); animation: scan 8s linear infinite; }}
    .title {{ font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; fill: #00ff00; filter: url(#greenGlow); }}
    .count {{ font-family: 'Courier New', monospace; font-size: 40px; font-weight: bold; fill: #00ff00; filter: url(#greenGlow); }}
  </style>
  
  <!-- Background -->
  <rect width="500" height="160" class="bg"/>
  
  <!-- Binary rain backdrop -->
  {"".join(binary_elements)}
  
  <!-- Circuit pattern -->
  {"".join(circuit_elements)}
  
  <!-- Terminal screen -->
  <rect x="30" y="15" width="200" height="130" class="terminal"/>
  
  <!-- Scanline effect -->
  <rect width="500" height="2" class="scanline"/>
  
  <!-- Glitch title -->
  {glitch_title}
  
  <!-- Code lines with typing effect -->
  {"".join(code_lines)}
  {cursor_blink}
  
  <!-- Digital counter -->
  <g>
    {"".join(counter_elements)}
  </g>
  
  <!-- Connection dots -->
  <circle cx="240" cy="80" r="3" fill="#00ff00" opacity="0.7">
    <animate attributeName="opacity" values="0.7;1;0.7" dur="2s" repeatCount="indefinite"/>
  </circle>
  <path d="M 240,80 L 260,80" stroke="#00ff00" stroke-width="2" opacity="0.5"/>
</svg>'''

    return Response(svg, mimetype='image/svg+xml')

@app.route('/update_views/<path:tag_name>', methods=['POST'])
def update_views(tag_name):
    """API endpoint to update view count for a repository tag"""
    tag_name = unquote(tag_name)
    
    current_date = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    existing_entry = views_collection.find_one({"tag": tag_name, "date": current_date})
    
    if existing_entry:
        views_collection.update_one(
            {"_id": existing_entry["_id"]},
            {"$inc": {"views": 1}}
        )
    else:
        views_collection.insert_one({
            "tag": tag_name,
            "date": current_date,
            "views": 1
        })
    
    return {"status": "success", "message": f"View count updated for {tag_name}"}


@app.route('/')
def home():
    return render_template('index.html')    

if __name__ == '__main__':
    app.run(debug=True)