
# async def main():
#     create_database()
#     application = ApplicationBuilder().token(BOT_TOKEN).build()

#     # Add handlers and scheduling as before
#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(CommandHandler("freegame", freegame))
#     aioschedule.every().day.at(SCRAPE_TIME).do(scrape_and_update)

#     # Create task *after* the bot is running
#     asyncio.create_task(scheduler()) # or application.create_task for v20+
    


#     try:
#         await application.run_polling()
#     finally:
#         await application.shutdown() # Ensure proper shutdown
