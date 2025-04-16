# Image Resizer

A PyQt5 application that resizes images to a target file size between 100-500KB.

## Features

- Resize single images to a target file size range
- Batch resize all images in a folder
- Adjustable target size range using sliders
- Preview of selected images
- Progress tracking with detailed logs
- Multithreaded processing for responsive UI

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- WebP (.webp)

## Installation

1. Ensure you have Python 3.6+ installed
2. Install the required dependencies:

```
pip install -r requirements.txt
```

## Usage

Run the application:

```
python main.py
```

### Resizing a Single Image

1. Click "Select Single Image"
2. Choose an image file
3. Select where to save the resized image
4. Wait for processing to complete

### Resizing Multiple Images

1. Click "Select Image Folder"
2. Choose a folder containing images
3. Select an output folder for the resized images
4. Wait for processing to complete

### Adjusting Target Size

Use the sliders to adjust the target file size range (100-500KB by default).

## How It Works

The application uses a combination of quality reduction and dimension scaling to achieve the target file size range. It iteratively adjusts these parameters until the image size falls within the specified range.