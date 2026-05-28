import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from . import Grabberu as app, user_collection

class InvestmentStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

class InvestmentType(Enum):
    STOCKS = "stocks"
    CRYPTO = "crypto"
    REAL_ESTATE = "real_estate"
    STARTUPS = "startups"
    COMMODITIES = "commodities"
    FOREX = "forex"
    NFT = "nft"
    DEFI = "defi"

class MarketTrend(Enum):
    BULL = "bull"
    BEAR = "bear"
    STAGNANT = "stagnant"

# Advanced investment options with more parameters
INVESTMENTS: Dict[InvestmentType, Dict] = {
    InvestmentType.STOCKS: {
        "name": "Blue-Chip Stocks",
        "risk": 15,
        "profit_range": (5, 25),
        "duration_range": (30, 120),  # in minutes for simulation
        "min_amount": 100,
        "max_amount": 10000,
        "trend_effect": 0.7  # how much market trend affects this
    },
    InvestmentType.CRYPTO: {
        "name": "Cryptocurrency",
        "risk": 30,
        "profit_range": (-20, 100),
        "duration_range": (15, 60),
        "min_amount": 50,
        "max_amount": 5000,
        "trend_effect": 0.9
    },
    InvestmentType.REAL_ESTATE: {
        "name": "Real Estate",
        "risk": 10,
        "profit_range": (8, 35),
        "duration_range": (60, 240),
        "min_amount": 500,
        "max_amount": 20000,
        "trend_effect": 0.4
    },
    InvestmentType.STARTUPS: {
        "name": "Startup Funding",
        "risk": 40,
        "profit_range": (-30, 300),
        "duration_range": (120, 360),
        "min_amount": 200,
        "max_amount": 10000,
        "trend_effect": 0.6
    },
    InvestmentType.COMMODITIES: {
        "name": "Commodities",
        "risk": 20,
        "profit_range": (-10, 50),
        "duration_range": (45, 180),
        "min_amount": 100,
        "max_amount": 15000,
        "trend_effect": 0.5
    },
    InvestmentType.FOREX: {
        "name": "Forex Trading",
        "risk": 25,
        "profit_range": (-15, 60),
        "duration_range": (10, 90),
        "min_amount": 50,
        "max_amount": 8000,
        "trend_effect": 0.8
    },
    InvestmentType.NFT: {
        "name": "NFT Market",
        "risk": 35,
        "profit_range": (-40, 150),
        "duration_range": (30, 120),
        "min_amount": 30,
        "max_amount": 3000,
        "trend_effect": 0.85
    },
    InvestmentType.DEFI: {
        "name": "DeFi Yield Farming",
        "risk": 45,
        "profit_range": (-50, 200),
        "duration_range": (60, 180),
        "min_amount": 75,
        "max_amount": 5000,
        "trend_effect": 0.95
    }
}

# Global market state
current_market_trend = MarketTrend.BULL
market_trend_last_change = datetime.now()
market_volatility = 1.0  # Multiplier for market fluctuations

async def update_market_trend():
    """Update the global market trend periodically"""
    global current_market_trend, market_trend_last_change, market_volatility
    
    while True:
        await asyncio.sleep(3600)  # Update every hour
        
        # Randomly change market trend
        trends = list(MarketTrend)
        new_trend = random.choice(trends)
        
        # Don't change to same trend
        while new_trend == current_market_trend:
            new_trend = random.choice(trends)
        
        current_market_trend = new_trend
        market_trend_last_change = datetime.now()
        
        # Update volatility (0.8 to 1.2 range)
        market_volatility = round(random.uniform(0.8, 1.2), 2)
        
        # Log the change (in a real bot, you might notify users)
        print(f"Market changed to {current_market_trend.value} trend with volatility {market_volatility}")

def get_market_effect() -> float:
    """Get the current market effect multiplier"""
    trend_multiplier = {
        MarketTrend.BULL: 1.2,
        MarketTrend.BEAR: 0.8,
        MarketTrend.STAGNANT: 1.0
    }
    return trend_multiplier[current_market_trend] * market_volatility

def format_time(minutes: int) -> str:
    """Format minutes into a human-readable string"""
    if minutes < 60:
        return f"{minutes} minutes"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours} hour{'s' if hours > 1 else ''}{f' {mins} minutes' if mins > 0 else ''}"

async def create_investment(user_id: int, amount: int, investment_type: InvestmentType) -> Dict:
    """Create a new investment"""
    investment_data = INVESTMENTS[investment_type]
    duration = random.randint(*investment_data["duration_range"])
    
    return {
        "type": investment_type.value,
        "name": investment_data["name"],
        "amount": amount,
        "invested_at": datetime.now(),
        "completes_at": datetime.now() + timedelta(minutes=duration),
        "status": InvestmentStatus.ACTIVE.value,
        "expected_profit_range": investment_data["profit_range"],
        "risk": investment_data["risk"],
        "duration": duration,
        "market_trend": current_market_trend.value,
        "volatility": market_volatility
    }

async def calculate_profit(investment: Dict) -> Dict:
    """Calculate the profit for a completed investment"""
    investment_type = InvestmentType(investment["type"])
    investment_data = INVESTMENTS[investment_type]
    
    # Base profit calculation
    min_profit, max_profit = investment_data["profit_range"]
    base_profit_percent = random.randint(min_profit, max_profit)
    
    # Apply market effects
    market_effect = get_market_effect() * investment_data["trend_effect"]
    adjusted_profit_percent = base_profit_percent * market_effect
    
    # Apply risk factor
    if random.randint(1, 100) <= investment_data["risk"]:
        # Risk triggered - bad outcome
        adjusted_profit_percent *= random.uniform(0.5, 1.5)  # Random modifier
        if adjusted_profit_percent > 0:
            adjusted_profit_percent = -adjusted_profit_percent  # Ensure loss
    
    # Calculate final profit
    profit = int((investment["amount"] * adjusted_profit_percent) / 100)
    final_amount = investment["amount"] + profit
    
    return {
        "profit": profit,
        "profit_percent": adjusted_profit_percent,
        "final_amount": final_amount,
        "status": InvestmentStatus.COMPLETED.value if final_amount >= investment["amount"] else InvestmentStatus.FAILED.value
    }

@app.on_message(filters.command(["invest", "inv"]))
async def invest_command(client: Client, message: Message):
    """Handle the invest command with interactive menu"""
    args = message.text.split()
    
    if len(args) == 1:
        # Show investment menu
        keyboard = []
        row = []
        
        for i, inv_type in enumerate(InvestmentType, start=1):
            inv_data = INVESTMENTS[inv_type]
            row.append(InlineKeyboardButton(
                f"{inv_data['name']}",
                callback_data=f"invest_info_{inv_type.value}"
            ))
            if i % 2 == 0:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        market_status = (
            f"📈 Current Market: {current_market_trend.value.upper()} "
            f"(Volatility: {market_volatility}x)\n"
            f"🔄 Last changed: {market_trend_last_change.strftime('%Y-%m-%d %H:%M')}\n\n"
            "Select an investment option below for details:"
        )
        
        await message.reply_text(
            f"💰 **Investment Opportunities** 💰\n\n{market_status}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if len(args) < 3:
        await message.reply_text(
            "⚠️ Usage: `/invest <amount> <type>`\n"
            "Example: `/invest 500 crypto`\n\n"
            "Use just `/invest` to see all options."
        )
        return
    
    try:
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("⚠️ Please enter a valid positive amount!")
        return
    
    inv_type_str = args[2].lower()
    try:
        inv_type = InvestmentType(inv_type_str)
    except ValueError:
        await message.reply_text(
            "⚠️ Invalid investment type! Use `/invest` to see available options."
        )
        return
    
    await process_investment(message, amount, inv_type)

async def process_investment(message: Message, amount: int, inv_type: InvestmentType):
    """Process a new investment"""
    user_id = message.from_user.id
    inv_data = INVESTMENTS[inv_type]
    
    # Validate amount
    if amount < inv_data["min_amount"]:
        await message.reply_text(
            f"⚠️ Minimum investment for {inv_data['name']} is {inv_data['min_amount']} coins!"
        )
        return
    
    if amount > inv_data["max_amount"]:
        await message.reply_text(
            f"⚠️ Maximum investment for {inv_data['name']} is {inv_data['max_amount']} coins!"
        )
        return
    
    # Check user balance
    user = await user_collection.find_one({"id": user_id})
    if not user or user.get("balance", 0) < amount:
        await message.reply_text(
            "❌ You don't have enough coins to make this investment!\n"
            f"Your balance: {user.get('balance', 0) if user else 0} | Needed: {amount}"
        )
        return
    
    # Create investment
    investment = await create_investment(user_id, amount, inv_type)
    
    # Deduct from balance
    await user_collection.update_one(
        {"id": user_id},
        {
            "$inc": {"balance": -amount},
            "$push": {"investments": investment}
        }
    )
    
    # Format completion time
    completes_at = investment["completes_at"]
    duration_str = format_time(investment["duration"])
    
    # Send confirmation
    reply_msg = (
        f"✅ **Investment Started!** ✅\n\n"
        f"📌 **Type:** {inv_data['name']}\n"
        f"💰 **Amount:** {amount} coins\n"
        f"⚠️ **Risk Level:** {inv_data['risk']}%\n"
        f"📊 **Market Trend:** {current_market_trend.value.upper()}\n"
        f"⏳ **Duration:** {duration_str}\n"
        f"🕒 **Completes At:** {completes_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        "You can check status with `/myinvestments`"
    )
    
    await message.reply_text(reply_msg)
    
    # Schedule completion check
    asyncio.create_task(complete_investment(user_id, investment, message))

async def complete_investment(user_id: int, investment: Dict, message: Message):
    """Complete an investment after its duration"""
    duration_minutes = investment["duration"]
    await asyncio.sleep(duration_minutes * 60)  # Convert to seconds
    
    # Get updated investment data
    user = await user_collection.find_one(
        {"id": user_id, "investments.status": InvestmentStatus.ACTIVE.value}
    )
    if not user:
        return
    
    # Find the specific investment
    active_investment = None
    for inv in user.get("investments", []):
        if (inv.get("status") == InvestmentStatus.ACTIVE.value and 
            inv.get("type") == investment["type"] and
            inv.get("amount") == investment["amount"] and
            inv.get("invested_at") == investment["invested_at"]):
            active_investment = inv
            break
    
    if not active_investment:
        return
    
    # Calculate profit
    result = await calculate_profit(active_investment)
    
    # Update user's investment and balance
    await user_collection.update_one(
        {
            "id": user_id,
            "investments": {
                "$elemMatch": {
                    "invested_at": investment["invested_at"],
                    "status": InvestmentStatus.ACTIVE.value
                }
            }
        },
        {
            "$set": {
                "investments.$.status": result["status"],
                "investments.$.completed_at": datetime.now(),
                "investments.$.profit": result["profit"],
                "investments.$.profit_percent": result["profit_percent"],
                "investments.$.final_amount": result["final_amount"]
            },
            "$inc": {"balance": result["profit"]}
        }
    )
    
    # Prepare result message
    if result["profit"] >= 0:
        emoji = "🎉"
        outcome = "PROFIT"
    else:
        emoji = "❌"
        outcome = "LOSS"
    
    profit_percent = result["profit_percent"]
    abs_profit = abs(result["profit"])
    
    result_msg = (
        f"{emoji} **Investment Completed!** {emoji}\n\n"
        f"📌 **Type:** {INVESTMENTS[InvestmentType(investment['type'])]['name']}\n"
        f"💰 **Invested:** {investment['amount']} coins\n"
        f"📊 **Market Trend:** {investment['market_trend'].upper()}\n"
        f"📈 **Volatility:** {investment['volatility']}x\n\n"
        f"💵 **Result:** {outcome} of {abs_profit} coins ({profit_percent:.2f}%)\n"
        f"🏦 **Final Amount:** {result['final_amount']} coins\n\n"
        f"{( 'Congratulations!' if outcome == 'PROFIT' else 'Better luck next time!' )}"
    )
    
    try:
        await message.reply_text(result_msg)
    except Exception as e:
        print(f"Couldn't send investment result: {e}")

@app.on_message(filters.command(["myinvestments", "myinv", "investments"]))
async def my_investments(client: Client, message: Message):
    """Show user's active and completed investments"""
    user_id = message.from_user.id
    user = await user_collection.find_one({"id": user_id})
    
    if not user or "investments" not in user or not user["investments"]:
        await message.reply_text("📭 You don't have any investments yet!")
        return
    
    active_inv = []
    completed_inv = []
    
    for inv in user["investments"]:
        if inv["status"] == InvestmentStatus.ACTIVE.value:
            active_inv.append(inv)
        else:
            completed_inv.append(inv)
    
    response = "📊 **Your Investments** 📊\n\n"
    
    if active_inv:
        response += "⏳ **Active Investments:**\n"
        for inv in active_inv:
            inv_type = InvestmentType(inv["type"])
            inv_data = INVESTMENTS[inv_type]
            
            time_left = inv["completes_at"] - datetime.now()
            minutes_left = max(0, int(time_left.total_seconds() / 60))
            time_left_str = format_time(minutes_left)
            
            response += (
                f"\n📌 **{inv_data['name']}**\n"
                f"💰 Amount: {inv['amount']} coins\n"
                f"⚠️ Risk: {inv_data['risk']}%\n"
                f"⏱ Time Left: {time_left_str}\n"
                f"🕒 Completes At: {inv['completes_at'].strftime('%Y-%m-%d %H:%M')}\n"
            )
    
    if completed_inv:
        response += "\n✅ **Completed Investments:**\n"
        for inv in completed_inv[-5:]:  # Show last 5 completed
            inv_type = InvestmentType(inv["type"])
            inv_data = INVESTMENTS[inv_type]
            
            profit = inv.get("profit", 0)
            profit_percent = inv.get("profit_percent", 0)
            outcome = "Profit" if profit >= 0 else "Loss"
            
            response += (
                f"\n📌 **{inv_data['name']}**\n"
                f"💰 Amount: {inv['amount']} coins\n"
                f"📈 Result: {outcome} of {abs(profit)} coins ({profit_percent:.2f}%)\n"
                f"🕒 Completed: {inv.get('completed_at', datetime.now()).strftime('%Y-%m-%d %H:%M')}\n"
            )
    
    await message.reply_text(response)

@app.on_message(filters.command(["topinvestors", "investorboard"]))
async def top_investors(client: Client, message: Message):
    """Show top investors leaderboard"""
    # Get top by total profit from investments
    pipeline = [
        {"$unwind": "$investments"},
        {"$match": {"investments.status": InvestmentStatus.COMPLETED.value}},
        {"$group": {
            "_id": "$id",
            "name": {"$first": "$name"},
            "total_profit": {"$sum": "$investments.profit"},
            "total_invested": {"$sum": "$investments.amount"},
            "investments_count": {"$sum": 1}
        }},
        {"$sort": {"total_profit": -1}},
        {"$limit": 10}
    ]
    
    top_investors = await user_collection.aggregate(pipeline).to_list(length=10)
    
    if not top_investors:
        await message.reply_text("📭 No investment data available yet!")
        return
    
    response = "🏆 **Top Investors Leaderboard** 🏆\n\n"
    response += "Rank | Investor | Profit | ROI | Investments\n"
    response += "----|---------|--------|-----|------------\n"
    
    for i, investor in enumerate(top_investors, 1):
        name = investor.get("name", "Anonymous")
        profit = investor["total_profit"]
        invested = investor["total_invested"]
        count = investor["investments_count"]
        
        roi = (profit / invested * 100) if invested > 0 else 0
        
        response += (
            f"{i}. {name[:15]} | "
            f"{profit:,} | "
            f"{roi:.1f}% | "
            f"{count}\n"
        )
    
    await message.reply_text(f"```{response}```")

@app.on_callback_query(filters.regex(r"^invest_info_"))
async def invest_info_callback(client: Client, callback_query):
    """Show detailed info about an investment type"""
    inv_type_str = callback_query.data.split("_")[-1]
    
    try:
        inv_type = InvestmentType(inv_type_str)
    except ValueError:
        await callback_query.answer("Invalid investment type!")
        return
    
    inv_data = INVESTMENTS[inv_type]
    
    # Calculate risk/reward emoji
    risk_emoji = "🔴" if inv_data["risk"] > 30 else "🟠" if inv_data["risk"] > 15 else "🟢"
    reward_emoji = "💰" * (3 if (inv_data["profit_range"][1] > 50) else 2 if (inv_data["profit_range"][1] > 25) else 1)
    
    # Market effect explanation
    market_effect = {
        MarketTrend.BULL: f"📈 Performs better in BULL markets (+{int(inv_data['trend_effect'] * 20)}% boost)",
        MarketTrend.BEAR: f"📉 Performs worse in BEAR markets (-{int(inv_data['trend_effect'] * 15)}% penalty)",
        MarketTrend.STAGNANT: "➡️ Less affected by market trends"
    }[current_market_trend]
    
    # Tips list
    tips = [
        'Diversify your portfolio to reduce risk',
        'Invest more during bull markets for better returns',
        'Higher risk investments can yield higher rewards',
        'Check market trends before investing',
        'Longer investments typically have more stable returns'
    ]
    
    # Create message
    message = (
        f"📊 **{inv_data['name']} Investment** 📊\n\n"
        f"{risk_emoji} **Risk Level:** {inv_data['risk']}%\n"
        f"{reward_emoji} **Profit Potential:** {inv_data['profit_range'][0]}% to {inv_data['profit_range'][1]}%\n"
        f"⏳ **Duration:** {format_time(inv_data['duration_range'][0])} to {format_time(inv_data['duration_range'][1])}\n"
        f"💰 **Investment Range:** {inv_data['min_amount']} to {inv_data['max_amount']} coins\n\n"
        f"{market_effect}\n"
        f"🔀 **Market Sensitivity:** {int(inv_data['trend_effect'] * 100)}%\n\n"
        f"💡 **Tip:** {random.choice(tips)}\n\n"
        f"To invest: `/invest <amount> {inv_type.value}`"
    )
    
    # Add buttons
    keyboard = [
        [InlineKeyboardButton("📈 Invest Now", callback_data=f"invest_now_{inv_type.value}")],
        [InlineKeyboardButton("🔙 Back to List", callback_data="invest_list")]
    ]
    
    await callback_query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
                      )

@app.on_callback_query(filters.regex(r"^invest_now_"))
async def invest_now_callback(client: Client, callback_query):
    """Handle invest now button"""
    inv_type_str = callback_query.data.split("_")[-1]
    
    try:
        inv_type = InvestmentType(inv_type_str)
    except ValueError:
        await callback_query.answer("Invalid investment type!")
        return
    
    await callback_query.answer(f"Please use /invest [amount] {inv_type.value}")
    await callback_query.edit_message_text(
        f"To invest in {INVESTMENTS[inv_type]['name']}, send:\n\n"
        f"`/invest [amount] {inv_type.value}`\n\n"
        f"Example: `/invest 500 {inv_type.value}`\n\n"
        f"Minimum: {INVESTMENTS[inv_type]['min_amount']} coins\n"
        f"Maximum: {INVESTMENTS[inv_type]['max_amount']} coins"
    )

@app.on_callback_query(filters.regex(r"^invest_list$"))
async def invest_list_callback(client: Client, callback_query):
    """Return to investment list"""
    keyboard = []
    row = []
    
    for i, inv_type in enumerate(InvestmentType, start=1):
        inv_data = INVESTMENTS[inv_type]
        row.append(InlineKeyboardButton(
            f"{inv_data['name']}",
            callback_data=f"invest_info_{inv_type.value}"
        ))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    market_status = (
        f"📈 Current Market: {current_market_trend.value.upper()} "
        f"(Volatility: {market_volatility}x)\n"
        f"🔄 Last changed: {market_trend_last_change.strftime('%Y-%m-%d %H:%M')}\n\n"
        "Select an investment option below for details:"
    )
    
    await callback_query.edit_message_text(
        f"💰 **Investment Opportunities** 💰\n\n{market_status}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def check_completed_investments():
    """Periodically check and complete expired investments"""
    while True:
        await asyncio.sleep(60)  # Check every minute
        
        now = datetime.now()
        users = user_collection.find({
            "investments": {
                "$elemMatch": {
                    "status": InvestmentStatus.ACTIVE.value,
                    "completes_at": {"$lte": now}
                }
            }
        })
        
        async for user in users:
            for inv in user["investments"]:
                if (inv["status"] == InvestmentStatus.ACTIVE.value and 
                    inv["completes_at"] <= now):
                    
                    # Calculate profit
                    result = await calculate_profit(inv)
                    
                    # Update investment
                    await user_collection.update_one(
                        {
                            "id": user["id"],
                            "investments": {
                                "$elemMatch": {
                                    "invested_at": inv["invested_at"],
                                    "status": InvestmentStatus.ACTIVE.value
                                }
                            }
                        },
                        {
                            "$set": {
                                "investments.$.status": result["status"],
                                "investments.$.completed_at": now,
                                "investments.$.profit": result["profit"],
                                "investments.$.profit_percent": result["profit_percent"],
                                "investments.$.final_amount": result["final_amount"]
                            },
                            "$inc": {"balance": result["profit"]}
                        }
                    )
                    
                    # Notify user (in a real bot, you'd send a message)
                    print(f"Completed investment for user {user['id']}: {result}")
