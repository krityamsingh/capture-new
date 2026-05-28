import random
import datetime
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from . import Grabberu as app, user_collection

# Enhanced Work System Configuration
WORK_DURATION = 8 * 60 * 60  # 8 hours in seconds
REMINDER_INTERVAL = 30 * 60  # 30 minutes in seconds

# Premium Break System with Emoji Art
BREAKS = [
    {
        "time": 2 * 60 * 60,
        "message": "🕒 **Break Time!** 🍵\n\n"
                   "```diff\n+ Take a 15-minute tea break!\n```\n"
                   "☕ Relax and recharge your energy!\n"
                   "━━━━━━━━━━━━━━\n"
                   f"⏳ Work Progress: 25% completed"
    },
    {
        "time": 4 * 60 * 60,
        "message": "🕛 **Lunch Hour!** 🍱\n\n"
                   "```fix\n! Enjoy a 30-minute lunch break\n```\n"
                   "🍜 Fuel up for the afternoon shift!\n"
                   "━━━━━━━━━━━━━━\n"
                   f"⏳ Work Progress: 50% completed"
    },
    {
        "time": 6 * 60 * 60,
        "message": "🕞 **Stretch Time!** 🧘\n\n"
                   "```python\n# Pro Tip: Standing up improves productivity by 27%\n```\n"
                   "🚶‍♂️ Take a quick walk and refresh!\n"
                   "━━━━━━━━━━━━━━\n"
                   f"⏳ Work Progress: 75% completed"
    },
]

# Premium Job List with Descriptions and Requirements
JOBS = {
    "🍕 Pizza Ninja": {
        "salary": (600, 1800),
        "desc": "Stealthily deliver pizzas with ninja precision!",
        "req": "Requires: Bike License 🏍️"
    },
    "🧹 Chaos Cleaner": {
        "salary": (400, 1200),
        "desc": "Bring order to the most chaotic spaces!",
        "req": "Requires: OCD Certification 📜"
    },
    "💻 Code Samurai": {
        "salary": (2500, 6000),
        "desc": "Battle bugs and slay inefficient algorithms!",
        "req": "Requires: Python Black Belt 🐍"
    },
    "🚗 Turbo Taxi": {
        "salary": (800, 2500),
        "desc": "Drive at ludicrous speed (safely)!",
        "req": "Requires: Need for Speed 🏎️"
    },
    "🎤 Karaoke Hero": {
        "salary": (500, 1500),
        "desc": "Save audiences from bad singing!",
        "req": "Requires: Golden Voice 🎶"
    },
    "🏦 Vault Guardian": {
        "salary": (1800, 3500),
        "desc": "Protect treasures from would-be thieves!",
        "req": "Requires: Poker Face 🃏"
    },
    "🔧 Machine Whisperer": {
        "salary": (900, 2000),
        "desc": "Fix what others can't with a gentle touch!",
        "req": "Requires: Toolbox 🧰"
    },
    "🎭 Drama Llama": {
        "salary": (3000, 7000),
        "desc": "Bring stories to life with extra flair!",
        "req": "Requires: Oscar Nomination 🏆"
    },
    "🤹‍♂️ Gravity Rebel": {
        "salary": (700, 1900),
        "desc": "Defy physics for audience amazement!",
        "req": "Requires: No Fear 😱"
    },
    "🔬 Mad Scientist": {
        "salary": (3500, 8000),
        "desc": "Create what shouldn't be possible!",
        "req": "Requires: Crazy Hair 👨‍🔬"
    },
}

# Active Work Tracking with Bonuses
active_jobs = {}

# Premium Work Command
@app.on_message(filters.command(["work", "jobs"]))
async def premium_work_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    mention = f"[{user_name}](tg://user?id={user_id})"

    # Check if already working
    if user_id in active_jobs:
        job_data = active_jobs[user_id]
        elapsed = (datetime.datetime.utcnow() - job_data["start_time"]).seconds
        remaining = WORK_DURATION - elapsed
        return await message.reply(
            f"⏳ **{mention}**, you're already working as a **{job_data['job']}**!\n"
            f"⏱️ Time remaining: {remaining//3600}h {(remaining%3600)//60}m\n\n"
            "```diff\n- Finish your current job before starting another!\n```"
        )

    # Create interactive job board
    buttons = []
    for job, details in JOBS.items():
        buttons.append([
            InlineKeyboardButton(
                f"{job} | ${details['salary'][0]}-{details['salary'][1]}",
                callback_data=f"work_select_{job}"
            )
        ])
    
    # Add help button
    buttons.append([InlineKeyboardButton("❓ How It Works", callback_data="work_help")])
    
    await message.reply(
        f"🏢 **{mention}**, welcome to the **Job Center**! 🏢\n\n"
        "```markdown\n# Available Positions:\n"
        "• Earn coins by working 8-hour shifts\n"
        "• Higher risk jobs pay better!\n"
        "• Bonuses for completing jobs!\n```\n"
        "🔍 Select your dream job below:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Job Help Callback
@app.on_callback_query(filters.regex(r"^work_help$"))
async def work_help(client, callback_query):
    await callback_query.answer()
    await callback_query.message.edit(
        "📊 **Job System Guide** 📊\n\n"
        "```prolog\n"
        "1. Select any available job\n"
        "2. Work for 8 hours (real-time)\n"
        "3. Earn salary + possible bonuses\n"
        "4. Take breaks when notified\n"
        "5. Complete to get paid!\n"
        "```\n"
        "💡 **Tips**:\n"
        "• Higher paying jobs are riskier!\n"
        "• Stay active for bonus rewards\n"
        "• Check back every 30 minutes\n\n"
        "⚠️ **Warning**: Leaving early forfeits payment!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Jobs", callback_data="work_back")]
        ])
    )

# Job Selection Callback
@app.on_callback_query(filters.regex(r"^work_select_(.+)"))
async def premium_job_selected(client, callback_query):
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name
    mention = f"[{user_name}](tg://user?id={user_id})"
    job_name = callback_query.data.split("_", 2)[2]

    # Handle back button
    if job_name == "back":
        buttons = []
        for job, details in JOBS.items():
            buttons.append([
                InlineKeyboardButton(
                    f"{job} | ${details['salary'][0]}-{details['salary'][1]}",
                    callback_data=f"work_select_{job}"
                )
            ])
        buttons.append([InlineKeyboardButton("❓ How It Works", callback_data="work_help")])
        
        await callback_query.message.edit(
            f"🏢 **{mention}**, welcome to the **Job Center**! 🏢\n\n"
            "🔍 Select your dream job below:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Handle actual job selection
    if job_name not in JOBS:
        return await callback_query.answer("⚠️ Job no longer available!", show_alert=True)

    if user_id in active_jobs:
        return await callback_query.answer("You're already working!", show_alert=True)

    # Start job with style
    job_data = JOBS[job_name]
    active_jobs[user_id] = {
        "job": job_name,
        "start_time": datetime.datetime.utcnow(),
        "checks": 0,
        "message_id": callback_query.message.id
    }

    await callback_query.message.edit(
        f"🎉 **{mention}**, you've been hired as a **{job_name}**!\n\n"
        f"```yaml\nJob Description: {job_data['desc']}\n"
        f"Requirements: {job_data['req']}\n"
        f"Potential Earnings: ${job_data['salary'][0]}-{job_data['salary'][1]}\n```\n"
        "🛠️ Your shift starts now! Good luck!\n"
        "━━━━━━━━━━━━━━\n"
        "💡 You'll receive progress updates every 30 minutes",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Work Progress", callback_data="work_status")]
        ])
    )

    # Start work process
    asyncio.create_task(premium_work_process(client, user_id, job_name))

async def premium_work_process(client, user_id, job_name):
    try:
        user = await client.get_users(user_id)
        mention = f"[{user.first_name}](tg://user?id={user_id})"
        job_data = JOBS[job_name]
        
        # Work progress updates
        total_checks = WORK_DURATION // REMINDER_INTERVAL
        for check in range(1, total_checks + 1):
            await asyncio.sleep(REMINDER_INTERVAL)

            # Check if user quit
            if user_id not in active_jobs:
                return

            # Update check-in count
            active_jobs[user_id]["checks"] = check
            
            # Special messages at certain intervals
            progress = check / total_checks
            if progress == 0.25:
                await client.send_message(
                    user_id,
                    f"🌅 **Morning Update** for {mention}\n\n"
                    f"You've completed 25% of your **{job_name}** shift!\n"
                    "```diff\n+ Early Bonus: $100 added to potential earnings!\n```"
                )
            elif progress == 0.5:
                await client.send_message(
                    user_id,
                    f"🌇 **Midday Report** for {mention}\n\n"
                    f"Halfway through your **{job_name}** shift!\n"
                    "```diff\n+ Consistency Bonus: $200 added!\n```"
                )
            elif progress == 0.75:
                await client.send_message(
                    user_id,
                    f"🌆 **Afternoon Alert** for {mention}\n\n"
                    f"75% done with **{job_name}**! Almost there!\n"
                    "```diff\n+ Final Push Bonus: $300 added!\n```"
                )

            # Send break notifications
            for break_info in BREAKS:
                if check * REMINDER_INTERVAL == break_info["time"]:
                    await client.send_message(user_id, break_info["message"])

        # Job completion
        if user_id in active_jobs:
            # Calculate earnings with bonuses
            base_salary = random.randint(job_data["salary"][0], job_data["salary"][1])
            bonus = 600  # From all stage bonuses
            total_earnings = base_salary + bonus
            
            # Update database
            user_data = await user_collection.find_one({'id': user_id})
            new_balance = user_data.get("balance", 0) + total_earnings
            await user_collection.update_one(
                {'id': user_id},
                {"$set": {"balance": new_balance}}
            )

            # Special completion message
            completion_messages = [
                f"🏆 **JOB MASTERED!** {mention} has completed **{job_name}** with flying colors!",
                f"🌟 **PERFECT SHIFT!** {mention} nailed the **{job_name}** position!",
                f"🎖️ **EMPLOYEE OF THE DAY!** {mention} finished their **{job_name}** shift!"
            ]

            await client.send_message(
                user_id,
                f"✨ **Shift Complete!** ✨\n\n"
                f"```prolog\n"
                f"Job: {job_name}\n"
                f"Base Salary: ${base_salary}\n"
                f"Performance Bonus: ${bonus}\n"
                f"Total Earned: ${total_earnings}\n"
                f"New Balance: ${new_balance}\n"
                f"```\n"
                f"{random.choice(completion_messages)}\n\n"
                f"⏳ You can work again in 1 hour",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💼 Work Again", callback_data="work_back")]
                ])
            )

            # Remove from active jobs
            del active_jobs[user_id]
    except Exception as e:
        print(f"Error in work process: {e}")
        if user_id in active_jobs:
            del active_jobs[user_id]

# Work Status Check
@app.on_callback_query(filters.regex(r"^work_status$"))
async def work_status(client, callback_query):
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name
    
    if user_id not in active_jobs:
        return await callback_query.answer("You're not currently working!", show_alert=True)
    
    job_data = active_jobs[user_id]
    elapsed = (datetime.datetime.utcnow() - job_data["start_time"]).seconds
    remaining = WORK_DURATION - elapsed
    progress = min(99, (elapsed/WORK_DURATION)*100)
    
    # Create progress bar
    progress_bar = "🟢" * int(progress/10) + "⚪" * (10 - int(progress/10))
    
    await callback_query.answer()
    await callback_query.message.edit(
        f"📊 **Work Status for {user_name}**\n\n"
        f"```prolog\n"
        f"Current Job: {job_data['job']}\n"
        f"Time Worked: {elapsed//3600}h {(elapsed%3600)//60}m\n"
        f"Time Remaining: {remaining//3600}h {(remaining%3600)//60}m\n"
        f"Progress: {progress:.1f}%\n"
        f"{progress_bar}\n"
        f"```\n"
        "💡 Keep going to earn your paycheck!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="work_status")]
        ])
    )

# Work Status Command (consistent with callback version)
@app.on_message(filters.command(["workstatus", "ws", "jobstatus"]))
async def work_status_command(client: Client, message: Message):
    user_id = message.from_user.id
    await show_work_status(client, user_id, message)

# Work Status Callback
@app.on_callback_query(filters.regex(r"^work_status$"))
async def work_status_callback(client, callback_query):
    user_id = callback_query.from_user.id
    await callback_query.answer()
    await show_work_status(client, user_id, callback_query.message)

# Unified Work Status Display Function
async def show_work_status(client, user_id, message_or_callback):
    user = await client.get_users(user_id)
    mention = f"[{user.first_name}](tg://user?id={user_id})"
    
    if user_id not in active_jobs:
        content = (
            f"ℹ️ **{mention}**, you're not currently working!\n\n"
            "Use /work to start a new job and earn coins 💰"
        )
        if isinstance(message_or_callback, Message):
            await message_or_callback.reply(content)
        else:
            await message_or_callback.edit(
                content,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💼 View Jobs", callback_data="work_back")]
                ])
            )
        return
    
    job_data = active_jobs[user_id]
    elapsed = (datetime.datetime.utcnow() - job_data["start_time"]).seconds
    remaining = WORK_DURATION - elapsed
    progress = min(99, (elapsed/WORK_DURATION)*100)
    
    # Enhanced Visual Elements
    progress_bar = (
        "🟩" * int(progress/10) + 
        "🟨" * (1 if 0 < progress % 10 < 5 else 0) + 
        "⬜" * (10 - int(progress/10) - (1 if 0 < progress % 10 < 5 else 0))
    )
    
    job_info = JOBS[job_data["job"]]
    min_earnings = job_info["salary"][0] + 600
    max_earnings = job_info["salary"][1] + 600
    
    # Time Formatting
    worked_str = f"{elapsed//3600}h {(elapsed%3600)//60}m {elapsed%60}s"
    remaining_str = f"{remaining//3600}h {(remaining%3600)//60}m {remaining%60}s"
    
    # Next Break Calculation
    next_break = None
    for break_info in sorted(BREAKS, key=lambda x: x["time"]):
        if elapsed < break_info["time"]:
            next_break = f"in {(break_info['time'] - elapsed)//60} minutes"
            break
    
    content = (
        f"📊 **Work Status for {mention}**\n\n"
        f"🏢 **Job:** `{job_data['job']}`\n"
        f"⏳ **Worked:** `{worked_str}`\n"
        f"⏱️ **Remaining:** `{remaining_str}`\n"
        f"📈 **Progress:** `{progress:.1f}%`\n"
        f"{progress_bar}\n\n"
        f"💰 **Earnings:** `${min_earnings}-{max_earnings}`\n"
        f"☕ **Next Break:** `{next_break or 'none'}`\n\n"
        f"ℹ️ *Auto-updates every 30 minutes*"
    )
    
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="work_status"),
            InlineKeyboardButton("❌ Quit", callback_data="work_quit_confirm")
        ]
    ])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.reply(content, reply_markup=reply_markup)
    else:
        await message_or_callback.edit(content, reply_markup=reply_markup)

# Quit Confirmation Dialog
@app.on_callback_query(filters.regex(r"^work_quit_confirm$"))
async def quit_confirm(client, callback_query):
    await callback_query.answer()
    await callback_query.message.edit(
        "⚠️ **Are you sure you want to quit your current job?**\n\n"
        "```diff\n- You will NOT receive any payment!\n- All progress will be lost!\n```",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, Quit", callback_data="work_quit"),
                InlineKeyboardButton("❌ Cancel", callback_data="work_status")
            ]
        ])
    )

# Actual Quit Handler
@app.on_callback_query(filters.regex(r"^work_quit$"))
async def quit_job(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in active_jobs:
        del active_jobs[user_id]
        await callback_query.message.edit(
            "❌ **Job Quit Successfully**\n\n"
            "```diff\n- All progress has been lost\n- No coins earned\n```\n"
            "You can start a new job anytime with /work",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💼 View Jobs", callback_data="work_back")]
            ])
        )
    else:
        await callback_query.answer("You're not currently working!", show_alert=True)
