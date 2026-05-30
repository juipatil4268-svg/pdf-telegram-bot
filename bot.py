import os
import zipfile
import shutil

from telegram import (
    Update,
    ReplyKeyboardMarkup,
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from pdf2image import convert_from_path
from PIL import Image
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import pikepdf
import pytesseract

# ==========================================
# CONFIG
# ==========================================

TOKEN = "8573067591:AAFgpiqQVHAInFodaIqOWxQibruXoVHshGo"

POPPLER_PATH = r"C:\poppler\Library\bin"

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# ==========================================
# USER DATA
# ==========================================

user_mode = {}
user_files = {}

# ==========================================
# CREATE USER FOLDER
# ==========================================

def get_user_folder(user_id):

    folder = f"temp/{user_id}"

    os.makedirs(folder, exist_ok=True)

    return folder

# ==========================================
# START COMMAND
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        ["PDF to JPG", "JPG to PDF"],
        ["Merge PDF", "Split PDF"],
        ["Compress PDF", "OCR PDF"],
        ["Image OCR"],
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Choose a tool:",
        reply_markup=reply_markup
    )

# ==========================================
# MENU HANDLER
# ==========================================

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    user_id = update.message.from_user.id

    user_mode[user_id] = text

    user_files[user_id] = []

    await update.message.reply_text(
        f"{text} selected.\nNow send files."
    )

# ==========================================
# PDF TO JPG
# ==========================================

async def pdf_to_jpg(update: Update, context: ContextTypes.DEFAULT_TYPE):

    folder = get_user_folder(
        update.message.from_user.id
    )

    document = update.message.document

    file = await document.get_file()

    pdf_path = os.path.join(
        folder,
        document.file_name
    )

    await file.download_to_drive(pdf_path)

    await update.message.reply_text(
        "Converting PDF to JPG..."
    )

    try:

        images = convert_from_path(
            pdf_path,
            poppler_path=POPPLER_PATH
        )

        zip_path = os.path.join(
            folder,
            "images.zip"
        )

        with zipfile.ZipFile(
            zip_path,
            "w"
        ) as zipf:

            for i, image in enumerate(images):

                image_path = os.path.join(
                    folder,
                    f"page_{i+1}.jpg"
                )

                image.save(
                    image_path,
                    "JPEG"
                )

                zipf.write(
                    image_path,
                    arcname=f"page_{i+1}.jpg"
                )

        await update.message.reply_document(
            document=open(zip_path, "rb")
        )

    except Exception as e:

        await update.message.reply_text(
            f"Error: {str(e)}"
        )

    shutil.rmtree(folder)

# ==========================================
# JPG TO PDF
# ==========================================

async def jpg_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    folder = get_user_folder(user_id)

    photo = update.message.photo[-1]

    file = await photo.get_file()

    image_path = os.path.join(
        folder,
        "image.jpg"
    )

    await file.download_to_drive(image_path)

    await update.message.reply_text(
        "Creating PDF..."
    )

    image = Image.open(image_path)

    pdf_path = os.path.join(
        folder,
        "output.pdf"
    )

    image.convert("RGB").save(pdf_path)

    await update.message.reply_document(
        document=open(pdf_path, "rb")
    )

    shutil.rmtree(folder)

# ==========================================
# MERGE PDF
# ==========================================

async def merge_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    folder = get_user_folder(user_id)

    document = update.message.document

    file = await document.get_file()

    pdf_path = os.path.join(
        folder,
        document.file_name
    )

    await file.download_to_drive(pdf_path)

    user_files[user_id].append(pdf_path)

    await update.message.reply_text(
        f"Added {document.file_name}\n"
        f"Send more PDFs or type /done"
    )

# ==========================================
# DONE MERGING
# ==========================================

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    if user_mode.get(user_id) != "Merge PDF":

        await update.message.reply_text(
            "Merge mode is not active."
        )

        return

    if len(user_files[user_id]) == 0:

        await update.message.reply_text(
            "No PDFs uploaded."
        )

        return

    await update.message.reply_text(
        "Merging PDFs..."
    )

    merger = PdfMerger()

    for pdf in user_files[user_id]:
        merger.append(pdf)

    folder = get_user_folder(user_id)

    output_path = os.path.join(
        folder,
        "merged.pdf"
    )

    merger.write(output_path)

    merger.close()

    await update.message.reply_document(
        document=open(output_path, "rb")
    )

    shutil.rmtree(folder)

# ==========================================
# SPLIT PDF
# ==========================================

async def split_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    folder = get_user_folder(
        update.message.from_user.id
    )

    document = update.message.document

    file = await document.get_file()

    pdf_path = os.path.join(
        folder,
        document.file_name
    )

    await file.download_to_drive(pdf_path)

    await update.message.reply_text(
        "Splitting PDF..."
    )

    reader = PdfReader(pdf_path)

    zip_path = os.path.join(
        folder,
        "split_pages.zip"
    )

    with zipfile.ZipFile(zip_path, "w") as zipf:

        for i, page in enumerate(reader.pages):

            writer = PdfWriter()

            writer.add_page(page)

            output_pdf = os.path.join(
                folder,
                f"page_{i+1}.pdf"
            )

            with open(output_pdf, "wb") as f:
                writer.write(f)

            zipf.write(
                output_pdf,
                arcname=f"page_{i+1}.pdf"
            )

    await update.message.reply_document(
        document=open(zip_path, "rb")
    )

    shutil.rmtree(folder)

# ==========================================
# COMPRESS PDF
# ==========================================

async def compress_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    folder = get_user_folder(
        update.message.from_user.id
    )

    document = update.message.document

    file = await document.get_file()

    input_pdf = os.path.join(
        folder,
        document.file_name
    )

    await file.download_to_drive(input_pdf)

    await update.message.reply_text(
        "Compressing PDF..."
    )

    output_pdf = os.path.join(
        folder,
        "compressed.pdf"
    )

    pdf = pikepdf.open(input_pdf)

    pdf.save(output_pdf)

    await update.message.reply_document(
        document=open(output_pdf, "rb")
    )

    shutil.rmtree(folder)

# ==========================================
# OCR PDF
# ==========================================

async def ocr_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    folder = get_user_folder(
        update.message.from_user.id
    )

    document = update.message.document

    file = await document.get_file()

    pdf_path = os.path.join(
        folder,
        document.file_name
    )

    await file.download_to_drive(pdf_path)

    await update.message.reply_text(
        "Performing OCR..."
    )

    try:

        images = convert_from_path(
            pdf_path,
            poppler_path=POPPLER_PATH
        )

        full_text = ""

        for i, image in enumerate(images):

            await update.message.reply_text(
                f"Reading page {i+1}..."
            )

            text = pytesseract.image_to_string(
                image,
                lang="eng"
            )

            full_text += (
                f"\n\n===== PAGE {i+1} =====\n\n"
            )

            full_text += text

        output_txt = os.path.join(
            folder,
            "ocr_text.txt"
        )

        with open(
            output_txt,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(full_text)

        await update.message.reply_document(
            document=open(output_txt, "rb")
        )

    except Exception as e:

        await update.message.reply_text(
            f"Error: {str(e)}"
        )

    shutil.rmtree(folder)

# ==========================================
# IMAGE OCR
# ==========================================

async def image_ocr(update: Update, context: ContextTypes.DEFAULT_TYPE):

    folder = get_user_folder(
        update.message.from_user.id
    )

    photo = update.message.photo[-1]

    file = await photo.get_file()

    image_path = os.path.join(
        folder,
        "image.jpg"
    )

    await file.download_to_drive(image_path)

    await update.message.reply_text(
        "Reading text from image..."
    )

    try:

        image = Image.open(image_path)

        text = pytesseract.image_to_string(
            image,
            lang="eng"
        )

        output_txt = os.path.join(
            folder,
            "image_ocr.txt"
        )

        with open(
            output_txt,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(text)

        await update.message.reply_document(
            document=open(output_txt, "rb")
        )

    except Exception as e:

        await update.message.reply_text(
            f"Error: {str(e)}"
        )

    shutil.rmtree(folder)

# ==========================================
# UNIVERSAL PDF ROUTER
# ==========================================

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    mode = user_mode.get(user_id)

    if mode == "PDF to JPG":

        await pdf_to_jpg(update, context)

    elif mode == "Merge PDF":

        await merge_pdf(update, context)

    elif mode == "Split PDF":

        await split_pdf(update, context)

    elif mode == "Compress PDF":

        await compress_pdf(update, context)

    elif mode == "OCR PDF":

        await ocr_pdf(update, context)

    else:

        await update.message.reply_text(
            "Please choose a tool first."
        )

# ==========================================
# UNIVERSAL PHOTO ROUTER
# ==========================================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    mode = user_mode.get(user_id)

    if mode == "JPG to PDF":

        await jpg_to_pdf(update, context)

    elif mode == "Image OCR":

        await image_ocr(update, context)

    else:

        await update.message.reply_text(
            "Please choose a tool first."
        )

# ==========================================
# INVALID FILE
# ==========================================

async def invalid_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Please send the correct file type."
    )

# ==========================================
# MAIN
# ==========================================

app = ApplicationBuilder().token(TOKEN).build()

# COMMANDS
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("done", done))

# MENU
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        menu
    )
)

# PDF ROUTER
app.add_handler(
    MessageHandler(
        filters.Document.PDF,
        handle_pdf
    )
)

# PHOTO ROUTER
app.add_handler(
    MessageHandler(
        filters.PHOTO,
        handle_photo
    )
)

# INVALID FILES
app.add_handler(
    MessageHandler(
        filters.ALL,
        invalid_file
    )
)

print("Bot running...")

app.run_polling()