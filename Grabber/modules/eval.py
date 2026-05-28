import os
import re
import asyncio
import subprocess
import sys
import traceback
from inspect import getfullargspec
from io import StringIO
from time import time
from typing import Optional, Tuple
import aiofiles
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import MessageAuthorRequired
from Grabber import db
from . import app as Client, dev_filter, capsify
from .block import block_cbq

class CodeExecutor:
    """Advanced code execution handler with safety features and utilities."""
    
    MAX_OUTPUT_LENGTH = 4096
    MAX_RUNTIME_DISPLAY = 10  # seconds
    
    @staticmethod
    async def execute_python(
        code: str, 
        client: Client, 
        message: Message,
        timeout: int = 10
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Execute Python code asynchronously with timeout."""
        exec_globals = {
            'client': client,
            'message': message,
            'app': client,
            'db': db,
            'loop': asyncio.get_event_loop(),
            '__name__': '__main__',
            '__package__': None,
            '__doc__': None,
        }
        
        stdout = StringIO()
        stderr = StringIO()
        exc = None
        
        # Redirect output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout
        sys.stderr = stderr
        
        try:
            # Timeout protection (compatible with older Python versions)
            try:
                if sys.version_info >= (3, 11):
                    async with asyncio.timeout(timeout):
                        exec(
                            "async def __aexec():\n" +
                            "\n".join(f"    {line}" for line in code.split("\n")),
                            exec_globals
                        )
                        await exec_globals['__aexec']()
                else:
                    # Fallback for Python < 3.11
                    await asyncio.wait_for(
                        asyncio.create_task(
                            CodeExecutor._execute_python_internal(code, exec_globals)
                        ),
                        timeout=timeout
                    )
            except asyncio.TimeoutError:
                exc = f"TimeoutError: Execution timed out ({timeout}s)"
            except Exception:
                exc = traceback.format_exc()
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
        return stdout.getvalue(), stderr.getvalue(), exc

    @staticmethod
    async def _execute_python_internal(code: str, exec_globals: dict):
        """Internal execution method for Python < 3.11 compatibility."""
        exec(
            "async def __aexec():\n" +
            "\n".join(f"    {line}" for line in code.split("\n")),
            exec_globals
        )
        await exec_globals['__aexec']()

    @staticmethod
    async def execute_shell(
        command: str,
        timeout: int = 30
    ) -> Tuple[Optional[str], Optional[str]]:
        """Execute shell command asynchronously with timeout."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024  # 1MB buffer
            )
            
            try:
                # Timeout handling compatible with Python < 3.11
                if sys.version_info >= (3, 11):
                    async with asyncio.timeout(timeout):
                        stdout, stderr = await process.communicate()
                else:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                return stdout.decode('utf-8'), stderr.decode('utf-8')
            except asyncio.TimeoutError:
                process.kill()
                return None, f"TimeoutError: Command timed out ({timeout}s)"
                
        except Exception as e:
            return None, str(e)

async def safe_edit_or_reply(message: Message, text: str, **kwargs):
    """Safely edit or reply to a message, handling MessageAuthorRequired."""
    try:
        if message.from_user and message.from_user.is_self:
            await message.edit_text(text=text, **kwargs)
        else:
            await message.reply(text=text, **kwargs)
    except MessageAuthorRequired:
        # Try to reply if we can't edit
        await message.reply(text=text, **kwargs)

@Client.on_message(
    filters.command("eval", prefixes=["!", "/", "."]) & dev_filter
)
async def advanced_eval(client: Client, message: Message):
    """Advanced code evaluation with rich features."""
    if len(message.command) < 2:
        return await safe_edit_or_reply(
            message, 
            text=capsify("❌ Please provide code to evaluate.")
        )
    
    try:
        code = message.text.split(maxsplit=1)[1]
    except IndexError:
        return await message.delete()
    
    # Check for dangerous operations
    if any(word in code.lower() for word in ['os.system', 'subprocess', 'eval', 'exec', '__import__']):
        return await safe_edit_or_reply(
            message, 
            text=capsify("⚠️ Dangerous operation detected!")
        )
    
    start_time = time()
    status_msg = await message.reply("🔄 Executing...")
    
    stdout, stderr, exc = await CodeExecutor.execute_python(code, client, message)
    
    execution_time = round(time() - start_time, 3)
    output = exc or stderr or stdout or "✅ Execution successful (no output)"
    
    # Format the output
    formatted_output = (
        f"📝 **Input:**\n```python\n{code[:500]}```\n\n"
        f"📤 **Output:**\n```\n{output.strip()[:3000]}```\n\n"
        f"⏱ **Time:** `{execution_time}s`"
    )
    
    # Prepare buttons
    buttons = [
        [
            InlineKeyboardButton("⏱ Time", callback_data=f"runtime {execution_time}s"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"eval_close_{message.from_user.id}")
        ]
    ]
    
    if len(formatted_output) > CodeExecutor.MAX_OUTPUT_LENGTH:
        async with aiofiles.open('eval_output.txt', 'w') as f:
            await f.write(output)
        
        await message.reply_document(
            'eval_output.txt',
            caption=f"📝 **Input:**\n`{code[:500]}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await status_msg.delete()
        await message.delete()
        os.remove('eval_output.txt')
    else:
        await safe_edit_or_reply(
            status_msg,
            text=formatted_output,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )

@Client.on_message(
    (filters.command("sh", prefixes=["!", "/", "."]) | 
     filters.command("shell", prefixes=["!", "/", "."])) & dev_filter
)
async def advanced_shell(client: Client, message: Message):
    """Advanced shell command execution with safety checks."""
    if len(message.command) < 2:
        return await safe_edit_or_reply(
            message,
            text="**Usage:**\n`/sh <command>`"
        )
    
    command = message.text.split(maxsplit=1)[1]
    
    # Basic command blacklist
    BLACKLIST = [
        'rm -rf', 'mkfs', 'dd', 'shutdown', 'reboot', 
        'poweroff', 'chmod 777', ':(){:|:&};:'
    ]
    
    if any(cmd in command for cmd in BLACKLIST):
        return await safe_edit_or_reply(
            message,
            text="⚠️ Dangerous command blocked!"
        )
    
    status_msg = await message.reply("🔄 Executing shell command...")
    start_time = time()
    
    stdout, stderr = await CodeExecutor.execute_shell(command)
    
    execution_time = round(time() - start_time, 3)
    output = stderr or stdout or "✅ Command executed (no output)"
    
    # Format the output
    formatted_output = (
        f"🖥 **Command:**\n```bash\n{command}```\n\n"
        f"📤 **Output:**\n```\n{output.strip()}```\n\n"
        f"⏱ **Time:** `{execution_time}s`"
    )
    
    if len(formatted_output) > CodeExecutor.MAX_OUTPUT_LENGTH:
        async with aiofiles.open('shell_output.txt', 'w') as f:
            await f.write(output)
        
        await message.reply_document(
            'shell_output.txt',
            caption=f"🖥 **Command:**\n`{command}`",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏱ Time", callback_data=f"runtime {execution_time}s")
            ]])
        )
        await status_msg.delete()
        await message.delete()
        os.remove('shell_output.txt')
    else:
        await safe_edit_or_reply(
            status_msg,
            text=formatted_output,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏱ Time", callback_data=f"runtime {execution_time}s"),
                InlineKeyboardButton("🗑 Delete", callback_data=f"eval_close_{message.from_user.id}")
            ]]),
            disable_web_page_preview=True
        )

@Client.on_callback_query(filters.regex(r"^runtime"))
@block_cbq
async def show_runtime(_, cq):
    runtime = cq.data.split(maxsplit=1)[1]
    await cq.answer(f"Execution time: {runtime}", show_alert=True)

@Client.on_callback_query(filters.regex(r"^eval_close_"))
@block_cbq
async def close_eval(_, cq):
    user_id = int(cq.data.split("_")[-1])
    if cq.from_user.id == user_id:
        await cq.message.delete()
    else:
        await cq.answer("You can't delete this!", show_alert=True)
