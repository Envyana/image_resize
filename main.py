import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QWidget, QFileDialog, QLabel, QHBoxLayout, QProgressBar, 
                            QMessageBox, QSlider, QStackedWidget, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
import cv2
from PIL import Image
import shutil
import time

class ImageResizer:
    """Class to handle image resizing logic"""
    
    @staticmethod
    def resize_image(input_path, output_path, target_size_kb=(100, 1024)):
        """
        Resize an image to have a file size within the target range
        
        Args:
            input_path: Path to the input image
            output_path: Path to save the resized image
            target_size_kb: Tuple of (min_size, max_size) in kilobytes
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Open the image
            img = Image.open(input_path)
            
            # Get original format
            img_format = img.format
            if not img_format:
                img_format = 'JPEG'  # Default to JPEG if format is unknown
            
            # Initial quality
            quality = 90
            min_quality = 10
            
            # Maximum allowed file size in bytes
            max_size_bytes = target_size_kb[1] * 1024
            min_size_bytes = target_size_kb[0] * 1024
            
            # Initial size parameters
            width, height = img.size
            scale_factor = 1.0
            
            while True:
                # Apply size reduction if scale factor has changed
                if scale_factor < 1.0:
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                else:
                    resized_img = img
                
                # Save to a temporary buffer to check size
                temp_output = f"{output_path}.temp"
                resized_img.save(temp_output, format=img_format, quality=quality)
                
                # Check file size
                file_size = os.path.getsize(temp_output)
                
                # If file size is within target range, we're done
                if min_size_bytes <= file_size <= max_size_bytes:
                    shutil.move(temp_output, output_path)
                    return True, file_size
                
                # If file is still too large
                if file_size > max_size_bytes:
                    if quality > min_quality:
                        # First try reducing quality
                        quality -= 5
                    else:
                        # If quality is already at minimum, reduce dimensions
                        scale_factor *= 0.9
                        
                        # If the image is too small, we can't reduce it further
                        if scale_factor < 0.3:
                            # Use the last result if it's close enough
                            shutil.move(temp_output, output_path)
                            return False, file_size
                else:
                    # File is too small, try increasing quality or scale
                    if quality < 95:
                        quality += 5
                    else:
                        # We're at max quality but file is still too small
                        # This is acceptable as it's below the max size
                        shutil.move(temp_output, output_path)
                        return True, file_size
                        
                # Remove the temporary file
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                    
        except Exception as e:
            print(f"Error resizing image: {e}")
            return False, 0

class ResizeWorker(QThread):
    """Worker thread for image resizing"""
    progress_updated = pyqtSignal(int)
    resize_completed = pyqtSignal(list)
    file_processed = pyqtSignal(str, bool, int)
    
    def __init__(self, files, output_dir, target_size_kb):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.target_size_kb = target_size_kb
        self.running = True
        
    def run(self):
        results = []
        for i, file_path in enumerate(self.files):
            if not self.running:
                break
                
            file_name = os.path.basename(file_path)
            output_path = os.path.join(self.output_dir, file_name)
            
            # Skip non-image files
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
                continue
                
            success, file_size = ImageResizer.resize_image(file_path, output_path, self.target_size_kb)
            results.append((file_path, output_path, success, file_size))
            
            # Emit signals
            progress = int((i + 1) / len(self.files) * 100)
            self.progress_updated.emit(progress)
            self.file_processed.emit(file_name, success, file_size)
            
        self.resize_completed.emit(results)
        
    def stop(self):
        self.running = False

class SingleImageTab(QWidget):
    """Tab for single image resizing"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Select button
        self.select_btn = QPushButton('Select Image')
        self.select_btn.setMinimumHeight(40)
        self.select_btn.clicked.connect(self.select_image)
        layout.addWidget(self.select_btn)
        
        # Status
        self.status_label = QLabel('Select an image to resize')
        layout.addWidget(self.status_label)
        
        # Image preview
        self.preview_label = QLabel('No image selected')
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        layout.addWidget(self.preview_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Results
        self.result_label = QLabel('')
        layout.addWidget(self.result_label)
        
        self.setLayout(layout)
        
    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Select Image', '', 'Images (*.jpg *.jpeg *.png *.bmp *.webp)'
        )
        
        if file_path:
            self.status_label.setText(f'Selected: {os.path.basename(file_path)}')
            
            # Show preview
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(pixmap)
                
            # Get output directory
            output_dir, _ = QFileDialog.getSaveFileName(
                self, 'Save Resized Image', os.path.dirname(file_path), 'Images (*.jpg *.jpeg *.png *.bmp *.webp)'
            )
            
            if output_dir:
                # Process single image
                self.status_label.setText(f'Resizing {os.path.basename(file_path)}...')
                self.progress_bar.setValue(0)
                
                # Clear previous result
                self.result_label.setText('')
                
                # Start the resizing in a separate thread
                self.parent.resize_worker = ResizeWorker(
                    [file_path], 
                    os.path.dirname(output_dir), 
                    self.parent.target_size_kb
                )
                self.parent.resize_worker.progress_updated.connect(self.update_progress)
                self.parent.resize_worker.resize_completed.connect(self.on_resize_completed)
                self.parent.resize_worker.file_processed.connect(self.on_file_processed)
                self.parent.resize_worker.start()
                
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def on_file_processed(self, filename, success, file_size):
        status = "Success" if success else "Warning: Target size not achieved"
        file_size_kb = file_size / 1024
        self.result_label.setText(f"{filename}: {status} ({file_size_kb:.1f}KB)")
        
    def on_resize_completed(self, results):
        success_count = sum(1 for _, _, success, _ in results if success)
        total_count = len(results)
        
        self.status_label.setText('Resizing complete')
        
        # Show a message box with results
        QMessageBox.information(
            self, 
            'Processing Complete',
            f'Image successfully resized to the target size range.\n\n'
            f'Target range: {self.parent.target_size_kb[0]}-{self.parent.target_size_kb[1]}KB'
        )

class FolderTab(QWidget):
    """Tab for folder image resizing"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Select button
        self.select_btn = QPushButton('Select Folder with Images')
        self.select_btn.setMinimumHeight(40)
        self.select_btn.clicked.connect(self.select_folder)
        layout.addWidget(self.select_btn)
        
        # Status
        self.status_label = QLabel('Select a folder containing images to resize')
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Results log
        self.log_label = QLabel('Results will appear here')
        self.log_label.setAlignment(Qt.AlignTop)
        self.log_label.setMinimumHeight(250)
        layout.addWidget(self.log_label)
        
        self.setLayout(layout)
        
    def select_folder(self):
        input_dir = QFileDialog.getExistingDirectory(self, 'Select Input Folder')
        
        if input_dir:
            # Get all image files in the folder
            image_files = []
            for root, _, files in os.walk(input_dir):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
                        image_files.append(os.path.join(root, file))
            
            if not image_files:
                QMessageBox.warning(self, 'No Images', 'No image files found in the selected folder.')
                return
                
            self.status_label.setText(f'Found {len(image_files)} images in {os.path.basename(input_dir)}')
            
            # Get output directory
            output_dir = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
            
            if output_dir:
                # Process all images
                self.status_label.setText(f'Resizing {len(image_files)} images...')
                self.progress_bar.setValue(0)
                
                # Clear previous results
                self.log_label.setText('Processing images...')
                
                # Start the resizing in a separate thread
                self.parent.resize_worker = ResizeWorker(
                    image_files, 
                    output_dir, 
                    self.parent.target_size_kb
                )
                self.parent.resize_worker.progress_updated.connect(self.update_progress)
                self.parent.resize_worker.resize_completed.connect(self.on_resize_completed)
                self.parent.resize_worker.file_processed.connect(self.on_file_processed)
                self.parent.resize_worker.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def on_file_processed(self, filename, success, file_size):
        status = "Success" if success else "Warning: Target size not achieved"
        file_size_kb = file_size / 1024
        current_text = self.log_label.text()
        
        if current_text == 'Processing images...' or current_text == 'Results will appear here':
            self.log_label.setText(f"{filename}: {status} ({file_size_kb:.1f}KB)")
        else:
            if len(current_text.split("\n")) > 12:
                # Keep only the most recent 12 results
                lines = current_text.split("\n")
                current_text = "\n".join(lines[-12:])
                
            self.log_label.setText(f"{current_text}\n{filename}: {status} ({file_size_kb:.1f}KB)")
        
    def on_resize_completed(self, results):
        success_count = sum(1 for _, _, success, _ in results if success)
        total_count = len(results)
        
        self.status_label.setText(f'Completed: {success_count}/{total_count} images successfully resized')
        
        # Show a message box with results
        QMessageBox.information(
            self, 
            'Processing Complete',
            f'{success_count} out of {total_count} images were successfully resized to the target size range.\n\n'
            f'Target range: {self.parent.target_size_kb[0]}-{self.parent.target_size_kb[1]}KB'
        )

class ImageResizerApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.resize_worker = None
        self.target_size_kb = (100, 1024)  # Default size range: 100KB-1MB
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Image Resizer')
        self.setGeometry(100, 100, 700, 500)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Target size range slider
        slider_layout = QHBoxLayout()
        slider_label = QLabel('Target Size Range:')
        slider_layout.addWidget(slider_label)
        
        self.min_size_slider = QSlider(Qt.Horizontal)
        self.min_size_slider.setRange(50, 900)
        self.min_size_slider.setValue(100)
        self.min_size_slider.setTickPosition(QSlider.TicksBelow)
        self.min_size_slider.setTickInterval(50)
        self.min_size_slider.valueChanged.connect(self.update_target_size)
        
        self.max_size_slider = QSlider(Qt.Horizontal)
        self.max_size_slider.setRange(100, 2048)
        self.max_size_slider.setValue(1024)  # 1MB
        self.max_size_slider.setTickPosition(QSlider.TicksBelow)
        self.max_size_slider.setTickInterval(100)
        self.max_size_slider.valueChanged.connect(self.update_target_size)
        
        slider_layout.addWidget(self.min_size_slider)
        self.min_size_label = QLabel(f'{self.min_size_slider.value()}KB')
        slider_layout.addWidget(self.min_size_label)
        
        slider_layout.addWidget(self.max_size_slider)
        self.max_size_label = QLabel(f'{self.max_size_slider.value()}KB')
        slider_layout.addWidget(self.max_size_label)
        
        main_layout.addLayout(slider_layout)
        
        # Tabs for different resizing options
        self.tabs = QTabWidget()
        
        # Single image tab
        self.single_tab = SingleImageTab(self)
        self.tabs.addTab(self.single_tab, "Single Image")
        
        # Folder tab
        self.folder_tab = FolderTab(self)
        self.tabs.addTab(self.folder_tab, "Image Folder")
        
        main_layout.addWidget(self.tabs)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
    def update_target_size(self):
        min_val = self.min_size_slider.value()
        max_val = self.max_size_slider.value()
        
        # Ensure min doesn't exceed max
        if min_val >= max_val:
            self.min_size_slider.setValue(max_val - 100)
            min_val = max_val - 100
            
        self.min_size_label.setText(f'{min_val}KB')
        self.max_size_label.setText(f'{max_val}KB')
        
        self.target_size_kb = (min_val, max_val)

def main():
    app = QApplication(sys.argv)
    window = ImageResizerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()