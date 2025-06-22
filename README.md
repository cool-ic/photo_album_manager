# Python Photo Album Manager

A web application for managing local photo and video libraries, built with Python (Flask) and JavaScript. This tool allows users to scan directories, view media, manage tags, and apply advanced filters using custom Python code.

## Key Features

*   **Media Organization & Viewing:**
    *   **Photo Wall:** Displays media in a responsive grid. Thumbnails are square-cropped and cached.
    *   **Configurable Layout:** Users can adjust the number of "Photos per Row," which dynamically changes thumbnail sizes.
    *   **Navigation:** Supports pagination for large libraries.
    *   **Image Viewer:** "X + Left-click" opens media in a full-size modal viewer with keyboard navigation (Left/Right arrows for prev/next, ESC to close).
    *   **Sorting:** Media can be sorted by capture time, modification time, filepath, or filename (ascending/descending). Missing EXIF capture times default to 1999-01-01.
    *   **Refresh:** A "Refresh" button rescans libraries and updates the view according to current filters and sort order.

*   **Tag Management:**
    *   **Global Tags:** Add or delete tags from a global list via the "Tag Management" modal. Deleting a global tag removes it from all associated media.
    *   **Quick Tagging:** Select tags from the info panel, then "T + Left-click" on a photo to apply those tags.
    *   **Batch Tagging:** Apply selected active tags to all currently selected photos using the "Batch Tag Selected" button.
    *   **Targeted Tag Removal:** "D + Left-click" on a specific tag displayed on a photo's thumbnail to remove only that tag from that photo.

*   **Advanced Filtering (Custom Python Code):**
    *   **Filter Configuration:** A modal allows users to input a Python function `api_select(media)` to define custom filtering logic.
    *   **`media` Object:** The `api_select` function receives a `media` object with the following attributes for decision making:
        *   `media.tags`: A list of tag strings associated with the media item (e.g., `['holiday', 'beach']`).
        *   `media.org_path`: The original library path string for the media item (e.g., `'/path/to/my/album1'`).
        *   `media.filename`: The filename (e.g., `'IMG_1234.jpg'`).
        *   `media.filepath`: The full absolute path to the file.
        *   `media.capture_time`: Python `datetime` object (or `None`).
        *   `media.modification_time`: Python `datetime` object.
        *   `media.filesize`: Integer, size in bytes.
        *   `media.media_type`: String, e.g., `'image'` or `'video'`.
        *   `media.id`: Integer, the database ID of the media item.
    *   **Enhanced Editor:** The input for the filter code uses a CodeMirror editor, providing Python syntax highlighting, line numbers, and better editing capabilities.
    *   **Filter Favorites:** Users can save frequently used filter snippets to their browser's `localStorage`, and then quickly load or delete them from a list within the filter modal.
    *   **Execution:** The provided Python code is executed directly by the server's Python interpreter.
        *   **Security Note:** No sandboxing (like `RestrictedPython`) is currently applied. Users should ensure any filter code is trusted.
        *   **Error Handling:** If the user's code is empty, has a syntax error, causes a runtime error, or doesn't define `api_select`, the filter will default to being permissive (showing all items). `print()` statements in the filter code will output to the server console.

*   **Media Management:**
    *   **Selection:**
        *   Left-click to select/deselect individual photos (visual border feedback). This also sets the anchor for range selection.
        *   Shift + Left-click on another photo to select all photos between the last non-shift clicked photo (anchor) and the current one.
    *   **Deletion:** "Delete Selected" button moves selected media items to a pre-configured archive path. The view is refreshed automatically.

*   **User Interface:**
    *   **Menu Bar (Left):** Contains controls for layout, sorting, refresh, filtering, tagging, and deletion.
    *   **Info Panel (Right):** Displays a list of all configured library organization paths (`org_path` values) and all globally defined tags, providing context for filter creation and tagging.
    *   **Session Isolation:** Different browser tabs or users will have independent filter configurations and selections due to session-based state management for filters.

*   **General Notes:**
    *   No user accounts or registration needed.
    *   Designed for managing personal photo libraries.
    *   Duplicate tagging on a photo has no effect.
    *   Destructive operations (deleting global tags, deleting photos) require user confirmation. Quick/batch tagging do not.
    *   Interrupting operations (applying filters, refresh, delete, sort) will reset photo selections.

## Technical Overview

*   **Backend:** Python with Flask framework, SQLAlchemy for ORM with an SQLite database.
*   **Frontend:** HTML, CSS, vanilla JavaScript. CodeMirror for the filter code editor.
*   **Data Storage:**
    *   Media metadata and tags: SQLite database (`data/photo_album.sqlite`).
    *   Thumbnails: Generated on demand and cached in `data/thumbnails/`.
    *   Filter Code Favorites: Browser `localStorage`.

## Setup Instructions

(These instructions are based on the project structure and common Python practices. Adjust if your setup differs.)

1.  **Clone the Repository (if applicable):**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>
    ```
    Ensure you are in the root project directory where `run.py` and `config.py` are located.

2.  **Create a Python Virtual Environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Paths in `config.py`:**
    *   Open `config.py`.
    *   Set `ORG_PATHS` to a list of absolute paths to your photo/video libraries. Example:
        ```python
        ORG_PATHS = [
            '/absolute/path/to/your/photos1',
            '/absolute/path/to/your/videos_and_photos2'
        ]
        ```
    *   Set `ARCHIVE_PATH` to an absolute path for where 'deleted' media should be moved. Example:
        ```python
        ARCHIVE_PATH = '/absolute/path/to/your/archive_folder'
        ```
    *   **Important:** Ensure the directories specified in `ORG_PATHS` and `ARCHIVE_PATH` exist on your system. Create them if they don't.

## Running the Application

1.  **Activate Virtual Environment** (if you created one).
2.  **Initial Media Scan (Important!):**
    This command populates the database with your media. Run it once when you first set up the application, and run it again whenever your photo libraries change significantly.
    ```bash
    flask scan libraries
    ```
3.  **Run the Flask Development Server:**
    ```bash
    python run.py
    ```
    The application is typically available at `http://127.0.0.1:5001/` (or as configured in `run.py`).

---

## 原始需求列表 (已根据当前实现修订)

### 后端

1.  **简洁核心**：无需任何冗余功能，不需要“用户”的概念，不需要注册，不需admin权限。
2.  **路径配置**：在Python后端代码中直接指定若干图片库的根路径（`ORG_PATHS`）。
3.  **图库定义**：每一个 `ORG_PATHS` 下的路径代表一个图库，该路径下的所有照片和视频均属于此图库。图库内部默认排序顺序为拍摄时间，也可按文件名排序。
4.  **标签系统**：
    *   支持为每张照片打上若干个标签（tag）。
    *   标签信息使用SQLite数据库存储，设计轻量，适用于十万量级的照片管理。
5.  **高级筛选功能**：
    *   允许用户通过自定义Python函数 `api_select(media)` 来筛选照片。
    *   **`media` 对象属性**：传递给 `api_select` 函数的 `media` 对象拥有以下可用属性：
        *   `media.tags`：一个包含该媒体所有标签名称（字符串）的列表。
        *   `media.org_path`：该媒体所属图库的原始路径（字符串）。
        *   `media.filename`：文件名（字符串）。
        *   `media.filepath`：文件的完整绝对路径（字符串）。
        *   `media.capture_time`：拍摄时间（datetime对象，可能为None）。
        *   `media.modification_time`：文件修改时间（datetime对象）。
        *   `media.filesize`：文件大小（整数，单位字节）。
        *   `media.media_type`：媒体类型，如 'image' 或 'video'（字符串）。
        *   `media.id`：媒体在数据库中的唯一ID（整数）。
    *   **示例函数**：
        ```python
        def api_select(media):
            # 检查标签列表是否包含 'animal'
            if 'animal' in media.tags:
                return False # 不显示带有 'animal' 标签的
            # 检查标签列表是否包含 'cat' 并且 原始路径是否包含 'old_photos'
            if 'cat' in media.tags and 'old_photos' in media.org_path:
                return True  # 显示在 old_photos 文件夹中的猫的图片
            return False # 其他情况默认不显示 (或根据需求返回 True 以显示)
        ```
    *   **安全提示**：用户提供的Python代码将由服务器直接执行，已移除`RestrictedPython`沙箱。请确保代码来源可靠，因为不再有安全沙箱的执行限制。如果代码有误（例如语法错误、运行时错误），筛选功能将默认允许所有图片通过（即显示所有图片）。

### 前端

#### 一、 查看照片功能

*   **feature1.1：照片墙展示**
    *   以照片墙形式展示图片，预览图自动裁剪为正方形并整齐排列。
    *   实现缩略图缓存策略以提高加载速度。
    *   **feature1.1.1【每行照片数 Photos per Row】**：用户可通过菜单栏控件调整每行展示的照片数量，预览图大小随之自适应缩放。
    *   **feature1.1.2【选择与查看 Select & View】**：
        *   左键单击图片可选中/取消选中该图片（并设定为范围选择的起始点）。
        *   按住【Shift键 + 左键单击】另一张图片，可选中这两张图片之间的所有图片（包含这两张）。
        *   按住【X键 + 左键单击】图片可查看原图。
        *   原图查看模式下，支持使用左右方向键切换上一张/下一张图片，按【ESC键】退出查看。
    *   **feature1.1.3【D+左键删除标签 D+Click to Remove Tag】**：在照片墙的缩略图上，当鼠标悬停于某个显示的标签上时，按下【D键 + 左键单击】该标签，即可从当前照片移除这一个特定标签。
    *   **feature1.1.4【翻页 Page Navigation】**：支持“上一页”、“下一页”翻页功能。

*   **feature1.2：信息看板 Info Panel**
    *   网页右侧固定显示信息看板（Backend Info），展示当前系统中所有存在的全局标签（Global Tag List）以及所有已配置的图库根路径（`org_path`列表）。此看板为用户编写自定义筛选函数时提供参考。

*   **feature1.3：高级筛选配置 Advanced Filter Configuration**
    *   菜单栏提供【筛选配置 Filter Config】按钮。
    *   点击后弹出高级筛选功能配置界面，用户可在此输入自定义的 `api_select(media)` Python函数。
    *   **编辑器升级**：输入框已升级为CodeMirror代码编辑器，提供Python语法高亮、行号、自动缩进等功能，提升编辑体验。
    *   **筛选代码收藏夹 Filter Code Favorites**：新增“收藏夹”功能，允许用户：
        *   将当前编辑器中的代码保存到收藏夹。
        *   查看已收藏的筛选代码片段列表。
        *   点击列表中的条目，可将其快速加载到编辑器中。
        *   从收藏夹中删除不需要的代码片段。
        *   此功能使用浏览器 `localStorage` 存储，收藏夹内容保留在用户本地浏览器中。
    *   点击“确定 Apply Filter”后，后端将根据提供的函数筛选照片，照片墙仅展示符合条件的图像。若函数为空或无效，则显示所有图像。

*   **feature1.4：会话隔离 Session Isolation**
    *   支持多用户或多标签页场景。不同用户在不同网页窗口使用各自的 `api_select(media)` 函数进行筛选时，状态通过Session机制管理，互不影响。

*   **feature1.5：刷新 Refresh**
    *   菜单栏提供【刷新 Refresh】按钮。点击后将重新扫描照片库（`ORG_PATHS`），并根据当前激活的筛选条件（若有）重新筛选并显示结果。

*   **feature1.6：排序 Sort By**
    *   菜单栏提供【排序 Sort By】控件，允许用户对当前显示的照片列表按照拍摄时间（`capture_time`）、文件修改时间（`modification_time`）或文件绝对路径（`filepath`）进行升序或降序排序。
    *   若照片（尤其是老照片或手机截图）缺少EXIF拍摄时间信息，则其拍摄时间被视为1999年1月1日零点。

*   **feature1.7：删除选中照片 Delete Selected Photos**
    *   菜单栏提供【删除选中 Delete Selected】按钮。
    *   所有被左键选中的照片将被移动到预设的归档路径（`ARCHIVE_PATH`）下，视为“最近删除”。
    *   文件名冲突时，通过添加后缀解决。
    *   每次删除操作后，将自动执行一次刷新（Refresh）操作。
    *   `ARCHIVE_PATH` 在后端Python代码中硬编码指定。

#### 二、 快捷打Tag模式功能

*   **feature2.1：标签管理 Tag Management**
    *   菜单栏提供【标签管理 Tag Management】按钮。
    *   点击后，用户可以管理全局标签列表（Global Tag List），包括：
        *   增加新标签到全局列表。
        *   从全局列表删除标签（此操作亦会从所有已关联该标签的图片上移除此标签）。

*   **feature2.2：快速单图打标签 Quick Single-Photo Tagging**
    *   用户可在右侧信息看板（feature1.2）中点击选择（激活）一个或多个全局标签（单击选中激活，再次单击取消激活，通过颜色区分激活状态）。
    *   随后，按住【T键 + 左键单击】任何照片墙上的图像，即可为该图像打上所有当前已激活的标签。

*   **feature2.3：批量选中打标签 Batch Tag Selected Photos**
    *   菜单栏提供【批量打标签 Batch Tag Selected】按钮。
    *   点击后，所有先前通过左键单击选中的图像，都将被打上当前在信息看板中处于激活状态的标签。

### 注意事项 (Notes)

*   **Note1（重复打标签）**: 给已经拥有某个特定标签的照片重复打上该标签，系统视为无操作，不会报错。
*   **Note2（菜单栏位置）**: 菜单栏固定位于网页左侧，不可隐藏或折叠。
*   **Note3（破坏性操作确认）**: 对于破坏性操作，如删除全局标签（会影响所有关联图片）和删除照片（移动到归档），在执行前应弹出确认框，要求用户二次确认。但快速单图打标签（T+左键）和批量选中打标签功能，则无需用户二次确认。
*   **Note4（中断操作重置）**: 每次执行中断性操作（如应用新筛选、刷新、删除照片、排序更改等），都会重置当前通过左键单击选中的照片集合。

---
