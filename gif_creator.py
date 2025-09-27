import tkinter as tk
from tkinter import messagebox, filedialog
import os
from PIL import Image, ImageTk, ImageSequence


def on_make_gif_clicked(root, home_frame, make_frame):
    home_frame.pack_forget()
    make_frame.pack(fill=tk.BOTH, expand=True)


def on_split_gif_clicked(root, home_frame, split_frame):
    home_frame.pack_forget()
    split_frame.pack(fill=tk.BOTH, expand=True)


STYLE_BG = "#f3f3f3"
BOX_RELIEF = tk.SUNKEN
BOX_BD = 1


def create_make_gif_frame(root, home_frame):
    frame = tk.Frame(root)

    # 状态
    selected_image_paths = []
    preview_photo = {"image": None}
    anim_photos = []
    anim_running = {"value": False}
    anim_index = {"value": 0}
    built_once = {"value": False}
    anim_after_id = {"id": None}

    # 布局框架：左侧控制区、右侧预览区
    frame.columnconfigure(0, weight=0, minsize=260)
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(0, weight=1)

    left = tk.Frame(frame)
    left.grid(row=0, column=0, sticky="nsew", padx=(10, 6), pady=10)
    right = tk.Frame(frame)
    right.grid(row=0, column=1, sticky="nsew", padx=(6, 10), pady=10)

    # 左侧布局
    for i in range(8):
        left.rowconfigure(i, weight=0)
    left.rowconfigure(3, weight=1)  # 列表区可拉伸
    left.columnconfigure(0, weight=1)
    left.columnconfigure(1, weight=1)

    btn_add = tk.Button(left, text="添加图片")
    btn_add.grid(row=0, column=0, columnspan=2, sticky="ew", ipady=3)

    listbox = tk.Listbox(left, relief=BOX_RELIEF, bd=BOX_BD)
    listbox.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(6, 6))

    btn_del_one = tk.Button(left, text="删除单张")
    btn_del_one.grid(row=2, column=0, sticky="ew")
    btn_clear = tk.Button(left, text="清空全部")
    btn_clear.grid(row=2, column=1, sticky="ew")

    # 参数：时长 + 循环
    tk.Label(left, text="时长(ms)").grid(row=4, column=0, sticky="w", pady=(8, 0))
    entry_duration = tk.Entry(left)
    entry_duration.grid(row=4, column=1, sticky="ew", pady=(8, 0))
    entry_duration.insert(0, "100")

    loop_var = tk.BooleanVar(value=True)
    def on_loop_toggle():
        # 若当前不在播放且已有帧，勾选后自动恢复播放
        if loop_var.get() and anim_photos and not anim_running["value"]:
            anim_running["value"] = True
            animate()
    chk_loop = tk.Checkbutton(left, text="循环播放", variable=loop_var, command=on_loop_toggle)
    chk_loop.grid(row=5, column=0, columnspan=2, sticky="w")

    # 参数：宽度高度（调整为同一行）
    tk.Label(left, text="宽度").grid(row=6, column=0, sticky="w", pady=(6, 0))
    entry_width = tk.Entry(left)
    entry_width.grid(row=6, column=1, sticky="ew", pady=(6, 0))
    tk.Label(left, text="高度").grid(row=7, column=0, sticky="w")
    entry_height = tk.Entry(left)
    entry_height.grid(row=7, column=1, sticky="ew")

    # 动作按钮
    btn_build_preview = tk.Button(left, text="生成预览")
    btn_build_preview.grid(row=8, column=0, sticky="ew", pady=(10, 0))
    btn_save = tk.Button(left, text="保存动图")
    btn_save.grid(row=8, column=1, sticky="ew", pady=(10, 0))

    # 右侧布局
    # 行0（图片预览）与行2（动图预览）均分可用高度
    right.rowconfigure(0, weight=1)
    right.rowconfigure(1, weight=0)
    right.rowconfigure(2, weight=1)
    right.rowconfigure(3, weight=0)
    right.columnconfigure(0, weight=1)

    lbl_preview = tk.Label(right, relief=BOX_RELIEF, bd=BOX_BD, bg=STYLE_BG)
    lbl_preview.grid(row=0, column=0, sticky="nsew")

    lbl_filename = tk.Label(right, anchor="w", text="")
    lbl_filename.grid(row=1, column=0, sticky="ew", pady=(4, 6))

    # 使用容器均分高度，避免 Label 图像请求影响布局
    gif_container = tk.Frame(right, relief=BOX_RELIEF, bd=BOX_BD, bg=STYLE_BG)
    gif_container.grid(row=2, column=0, sticky="nsew")
    gif_container.grid_propagate(True)
    lbl_gif_preview = tk.Label(gif_container, bg=STYLE_BG)
    lbl_gif_preview.pack(expand=True, fill="both")

    btn_play_pause = tk.Button(right, text="播放/暂停")
    btn_play_pause.grid(row=3, column=0, sticky="w", pady=(8, 0))

    # 功能
    def _get_widget_size(widget, fallback):
        w = widget.winfo_width()
        h = widget.winfo_height()
        if w <= 1 or h <= 1:
            return fallback
        return (w, h)

    def _get_equal_preview_sizes():
        # 让图片预览与动图预览高度均分（除去文件名与按钮）
        root.update_idletasks()
        total_w = max(1, right.winfo_width())
        total_h = max(1, right.winfo_height())
        name_h = max(0, lbl_filename.winfo_height())
        ctrl_h = max(0, btn_play_pause.winfo_height())
        rest_h = max(1, total_h - name_h - ctrl_h)
        each_h = max(60, rest_h // 2)
        return (total_w, each_h)

    def refresh_image_preview(index):
        if index < 0 or index >= len(selected_image_paths):
            lbl_preview.config(image="", text="")
            lbl_filename.config(text="")
            preview_photo["image"] = None
            return
        path = selected_image_paths[index]
        lbl_filename.config(text=path)
        try:
            img = Image.open(path)
            target_w, target_h = _get_equal_preview_sizes()
            ratio = min(target_w / img.width, target_h / img.height)
            new_w = max(1, int(img.width * ratio))
            new_h = max(1, int(img.height * ratio))
            img = img.resize((new_w, new_h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            preview_photo["image"] = photo
            lbl_preview.config(image=photo)
        except Exception as e:
            messagebox.showerror("错误", f"无法预览图片:\n{e}")

    def on_add_images():
        files = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                ("所有文件", "*.*"),
            ],
        )
        if not files:
            return
        for f in files:
            selected_image_paths.append(f)
            listbox.insert(tk.END, f)
        if listbox.size() > 0:
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(0)
            refresh_image_preview(0)

    def on_delete_selected():
        sel = listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        listbox.delete(idx)
        del selected_image_paths[idx]
        if listbox.size() > 0:
            new_idx = min(idx, listbox.size() - 1)
            listbox.selection_set(new_idx)
            refresh_image_preview(new_idx)
        else:
            refresh_image_preview(-1)

    def on_clear_all():
        listbox.delete(0, tk.END)
        selected_image_paths.clear()
        refresh_image_preview(-1)

    def on_listbox_select(event):
        sel = listbox.curselection()
        if not sel:
            return
        refresh_image_preview(sel[0])

    def build_anim_frames():
        anim_photos.clear()
        if not selected_image_paths:
            return False
        try:
            duration_ms = int(entry_duration.get().strip() or "100")
        except ValueError:
            messagebox.showerror("错误", "时长必须是数字（毫秒）")
            return False
        try:
            target_w = int(entry_width.get().strip()) if entry_width.get().strip() else None
            target_h = int(entry_height.get().strip()) if entry_height.get().strip() else None
        except ValueError:
            messagebox.showerror("错误", "宽度/高度必须是整数")
            return False

        # 使用均分后的容器尺寸作为动图帧尺寸基准
        preview_area_w, preview_area_h = _get_equal_preview_sizes()
        for p in selected_image_paths:
            img = Image.open(p).convert("RGBA")
            if target_w and target_h:
                img = img.resize((max(1, target_w), max(1, target_h)), Image.LANCZOS)
            ratio = min(preview_area_w / img.width, preview_area_h / img.height)
            disp_w = max(1, int(img.width * ratio))
            disp_h = max(1, int(img.height * ratio))
            disp_img = img.resize((disp_w, disp_h), Image.LANCZOS)
            anim_photos.append(ImageTk.PhotoImage(disp_img))
        lbl_gif_preview.duration_ms = duration_ms
        built_once["value"] = True
        return True

    def _cancel_timer():
        if anim_after_id["id"] is not None:
            try:
                root.after_cancel(anim_after_id["id"])
            except Exception:
                pass
            anim_after_id["id"] = None

    def animate():
        if not anim_running["value"] or not anim_photos:
            _cancel_timer()
            return
        idx = anim_index["value"]
        lbl_gif_preview.config(image=anim_photos[idx])
        delay = max(1, int(getattr(lbl_gif_preview, "duration_ms", 100)))
        if loop_var.get():
            anim_index["value"] = (idx + 1) % len(anim_photos)
            _cancel_timer()
            anim_after_id["id"] = root.after(delay, animate)
        else:
            if idx + 1 < len(anim_photos):
                anim_index["value"] = idx + 1
                _cancel_timer()
                anim_after_id["id"] = root.after(delay, animate)
            else:
                anim_running["value"] = False
                _cancel_timer()

    def on_build_preview():
        ok = build_anim_frames()
        if not ok:
            return
        anim_index["value"] = 0
        anim_running["value"] = True
        _cancel_timer()
        animate()

    def on_play_pause():
        if not anim_photos:
            if not build_anim_frames():
                return
        if anim_running["value"]:
            # 正在播放 -> 暂停
            anim_running["value"] = False
            _cancel_timer()
        else:
            # 暂停 -> 播放
            anim_running["value"] = True
            _cancel_timer()
            animate()

    def on_save_gif():
        if not selected_image_paths:
            messagebox.showwarning("提示", "请先添加至少一张图片")
            return
        try:
            duration_ms = int(entry_duration.get().strip() or "100")
        except ValueError:
            messagebox.showerror("错误", "时长必须是数字（毫秒）")
            return
        try:
            target_w = int(entry_width.get().strip()) if entry_width.get().strip() else None
            target_h = int(entry_height.get().strip()) if entry_height.get().strip() else None
        except ValueError:
            messagebox.showerror("错误", "宽度/高度必须是整数")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".gif",
            filetypes=[("GIF 动图", "*.gif")],
            title="保存动图"
        )
        if not save_path:
            return
        try:
            frames = []
            for p in selected_image_paths:
                img = Image.open(p)
                # 确保图片有透明通道
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                if target_w and target_h:
                    img = img.resize((max(1, target_w), max(1, target_h)), Image.LANCZOS)
                frames.append(img)
            
            # 检查是否有透明像素
            has_transparency = False
            for frame in frames:
                if frame.mode == 'RGBA':
                    # 检查是否有真正的透明像素（alpha < 255）
                    if 'transparency' in frame.info or frame.mode == 'RGBA':
                        # 更精确的透明检测
                        if frame.mode == 'RGBA':
                            # 获取alpha通道
                            alpha = frame.split()[-1]
                            # 检查是否有非完全不透明的像素
                            if alpha.getextrema()[0] < 255:
                                has_transparency = True
                                break
            
            save_kwargs = dict(
                save_all=True,
                append_images=frames[1:],
                duration=max(1, duration_ms),
                optimize=False,
                disposal=2,
            )
            
            # 如果有透明背景，使用RGBA模式保存
            if has_transparency:
                save_kwargs["save_all"] = True
                # 保持RGBA模式以保留透明信息
                frames[0].save(save_path, **save_kwargs)
            else:
                # 没有透明背景时，转换为P模式以减小文件大小
                p_frames = []
                for frame in frames:
                    p_frames.append(frame.convert("P", palette=Image.ADAPTIVE))
                save_kwargs["append_images"] = p_frames[1:]
                p_frames[0].save(save_path, **save_kwargs)
            
            # 循环播放：勾选则 loop=0（无限），不勾选则不写 loop 参数（只播放一遍）
            if loop_var.get():
                # 重新保存以添加loop参数
                temp_frames = frames if has_transparency else p_frames
                save_kwargs["loop"] = 0
                temp_frames[0].save(save_path, **save_kwargs)
            messagebox.showinfo("成功", "动图已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败:\n{e}")

    # 自适应：窗口尺寸变化时，刷新预览与动图帧
    _resize_job = {"id": None}

    def on_frame_configure(event=None):
        if _resize_job["id"] is not None:
            root.after_cancel(_resize_job["id"])
        def _do():
            sel = listbox.curselection()
            if sel:
                refresh_image_preview(sel[0])
            if built_once["value"]:
                running = anim_running["value"]
                if running:
                    anim_running["value"] = False
                build_anim_frames()
                anim_index["value"] = 0
                if running:
                    anim_running["value"] = True
                    _cancel_timer()
                    animate()
        _resize_job["id"] = root.after(150, _do)

    frame.bind("<Configure>", on_frame_configure)

    # 右下角返回按钮：返回主界面并停止动画
    def on_back_to_home():
        # 停止动画
        if 'anim_running' in locals():
            anim_running["value"] = False
        if 'anim_after_id' in locals() and anim_after_id["id"] is not None:
            try:
                root.after_cancel(anim_after_id["id"])
            except Exception:
                pass
            anim_after_id["id"] = None
        # 切换界面
        frame.pack_forget()
        home_frame.pack(expand=True)

    btn_back = tk.Button(right, text="返回", command=on_back_to_home)
    btn_back.grid(row=3, column=0, sticky="e", pady=(8, 0))

    btn_add.config(command=on_add_images)
    btn_del_one.config(command=on_delete_selected)
    btn_clear.config(command=on_clear_all)
    listbox.bind("<<ListboxSelect>>", on_listbox_select)
    btn_build_preview.config(command=on_build_preview)
    btn_play_pause.config(command=on_play_pause)
    btn_save.config(command=on_save_gif)

    return frame


def create_split_gif_frame(root, home_frame):
    frame = tk.Frame(root)

    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    frame.rowconfigure(1, weight=0)

    container = tk.Frame(frame)
    container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    for i in range(3):
        container.rowconfigure(i, weight=0)
    container.columnconfigure(0, weight=0)
    container.columnconfigure(1, weight=1)
    container.columnconfigure(2, weight=0)

    # 选择 GIF 文件
    tk.Label(container, text="选择 GIF 文件：").grid(row=0, column=0, sticky="w")
    gif_path_var = tk.StringVar()
    entry_gif_path = tk.Entry(container, textvariable=gif_path_var)
    entry_gif_path.grid(row=0, column=1, sticky="ew", padx=(6, 6))
    btn_choose_gif = tk.Button(container, text="浏览...")
    btn_choose_gif.grid(row=0, column=2, sticky="ew")

    # 输出目录
    tk.Label(container, text="输出目录：").grid(row=1, column=0, sticky="w", pady=(8, 0))
    out_dir_var = tk.StringVar()
    entry_out_dir = tk.Entry(container, textvariable=out_dir_var)
    entry_out_dir.grid(row=1, column=1, sticky="ew", padx=(6, 6), pady=(8, 0))
    btn_choose_out = tk.Button(container, text="选择...")
    btn_choose_out.grid(row=1, column=2, sticky="ew", pady=(8, 0))

    # 提示/占位统一方框
    info_box = tk.Label(container, relief=BOX_RELIEF, bd=BOX_BD, bg=STYLE_BG,
                        anchor="center", height=8,
                        text="拆解动图：\n选择 GIF 与输出目录后点击“分解动图”")
    info_box.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(10, 10))

    btn_extract = tk.Button(container, text="分解动图")
    btn_extract.grid(row=3, column=0, columnspan=3, sticky="ew")

    # 返回按钮
    def back_to_home():
        frame.pack_forget()
        home_frame.pack(expand=True)

    btn_back = tk.Button(frame, text="返回", command=back_to_home)
    btn_back.grid(row=1, column=0, sticky="e", padx=10, pady=(0, 10))

    def on_choose_gif():
        path = filedialog.askopenfilename(title="选择 GIF 文件",
                                          filetypes=[("GIF 文件", "*.gif"), ("所有文件", "*.*")])
        if path:
            gif_path_var.set(path)

    def on_choose_out():
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            out_dir_var.set(directory)

    def on_extract():
        gif_path = gif_path_var.get().strip()
        out_dir = out_dir_var.get().strip()
        if not gif_path:
            messagebox.showwarning("提示", "请先选择 GIF 文件")
            return
        if not out_dir:
            messagebox.showwarning("提示", "请先选择输出目录")
            return
        try:
            im = Image.open(gif_path)
            index = 0
            for frame_img in ImageSequence.Iterator(im):
                # 确保保持透明背景
                if frame_img.mode != 'RGBA':
                    rgba = frame_img.convert("RGBA")
                else:
                    rgba = frame_img.copy()
                
                filename = f"frame_{index:04d}.png"
                # 保存为PNG格式以保持透明背景
                rgba.save(os.path.join(out_dir, filename), "PNG")
                index += 1
            messagebox.showinfo("成功", f"共导出 {index} 帧")
        except Exception as e:
            messagebox.showerror("错误", f"拆解失败:\n{e}")

    btn_choose_gif.config(command=on_choose_gif)
    btn_choose_out.config(command=on_choose_out)
    btn_extract.config(command=on_extract)

    return frame


def create_main_window():
    root = tk.Tk()
    root.title("动图工具")

    # 初始大小，可调整
    root.geometry("600x450")
    root.minsize(600, 450)
    root.resizable(True, True)

    # 主界面
    home_frame = tk.Frame(root)
    home_frame.pack(expand=True)

    make_frame = create_make_gif_frame(root, home_frame)
    split_frame = create_split_gif_frame(root, home_frame)

    make_btn = tk.Button(
        home_frame,
        text="制作动图",
        width=18,
        height=2,
        command=lambda: on_make_gif_clicked(root, home_frame, make_frame),
    )
    split_btn = tk.Button(
        home_frame,
        text="拆解动图",
        width=18,
        height=2,
        command=lambda: on_split_gif_clicked(root, home_frame, split_frame),
    )

    make_btn.pack(pady=(0, 12))
    split_btn.pack()

    return root


if __name__ == "__main__":
    app = create_main_window()
    app.mainloop()