import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import logging

# Configure logging to write to a basic application log
logging.basicConfig(
    filename='renamer_history.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class EpisodeRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Episode Increment Renamer")
        self.root.geometry("900x600")
        
        # State variables
        self.current_folder = ""
        self.files_data = []      # List of dictionaries holding metadata for each file
        self.last_operation = []  # Stack of (new_path, old_path) tuples for the Undo feature
        
        self.setup_ui()
        
    def setup_ui(self):
        """Sets up the Tkinter GUI layout."""
        # --- Top Frame for Controls ---
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        self.folder_var = tk.StringVar(value="No folder selected")
        ttk.Label(top_frame, textvariable=self.folder_var, width=50, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(top_frame, text="Select Folder", command=self.select_folder).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(top_frame, text="Increment:").pack(side=tk.LEFT)
        self.increment_var = tk.IntVar(value=1)
        self.increment_spin = ttk.Spinbox(
            top_frame, from_=-100, to=100, textvariable=self.increment_var, width=5, command=self.update_preview
        )
        self.increment_spin.pack(side=tk.LEFT, padx=(5, 20))
        
        # Re-evaluate preview whenever the increment field is typed into (on key release)
        self.increment_spin.bind("<KeyRelease>", lambda e: self.update_preview())

        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top_frame, text="Dry Run (Safe mode)", variable=self.dry_run_var).pack(side=tk.LEFT)

        # --- Main Frame for Treeview (File List/Preview) ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("rel_dir", "old_name", "new_name", "status")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", selectmode="extended")
        
        self.tree.heading("rel_dir", text="Folder")
        self.tree.heading("old_name", text="Original Name")
        self.tree.heading("new_name", text="Preview New Name")
        self.tree.heading("status", text="Status")
        
        self.tree.column("rel_dir", width=150)
        self.tree.column("old_name", width=300)
        self.tree.column("new_name", width=300)
        self.tree.column("status", width=100)
        
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Re-evaluate preview whenever the selection changes
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_preview())

        # --- Bottom Frame for Actions ---
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.X)
        
        ttk.Button(bottom_frame, text="Rename Selected", command=self.execute_rename).pack(side=tk.RIGHT, padx=(10, 0))
        self.undo_btn = ttk.Button(bottom_frame, text="Undo Last Rename", command=self.undo_rename, state=tk.DISABLED)
        self.undo_btn.pack(side=tk.RIGHT)
        
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(bottom_frame, textvariable=self.status_var).pack(side=tk.LEFT)

    def select_folder(self):
        """Show folder selection dialog and trigger scanning if a folder is selected."""
        folder = filedialog.askdirectory()
        if folder:
            self.current_folder = folder
            self.folder_var.set(f"Target: {folder}")
            self.scan_folder()

    def scan_folder(self):
        """Recursively scan for video files containing standard SXXEXX episode notation."""
        self.files_data.clear()
        self.tree.delete(*self.tree.get_children())
        
        exts = {".mkv", ".mp4", ".avi", ".mov"}
        # Regular expression:
        # (?i) makes it case insensitive.
        # Group 1 captures Season part: e.g., 'S03'
        # Group 2 captures Episode part: e.g., 'E01'
        pattern = re.compile(r'(?i)(S\d+)(E\d+)')
        
        for root, _, files in os.walk(self.current_folder):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in exts:
                    match = pattern.search(file)
                    if match:
                        rel_dir = os.path.relpath(root, self.current_folder)
                        if rel_dir == ".":
                            rel_dir = ""
                        
                        full_path = os.path.join(root, file)
                        
                        item_id = self.tree.insert("", tk.END, values=(rel_dir, file, "", ""))
                        
                        self.files_data.append({
                            "id": item_id,
                            "full_path": full_path,
                            "root": root,
                            "old_name": file,
                            "match": match
                        })
        
        self.status_var.set(f"Found {len(self.files_data)} matching video files.")
        # Auto-select all matching files by default 
        for item in self.tree.get_children():
            self.tree.selection_add(item)
            
        self.update_preview()

    def calculate_new_name(self, old_name, match, increment):
        """Calculate the new file name by incrementing the parsed episode number."""
        season_part = match.group(1)
        episode_part = match.group(2)
        
        # Episode string looks like "E01"
        prefix = episode_part[0]  # Store 'E' or 'e'
        num_str = episode_part[1:] # The numeric trailing part, maybe zero padded
        
        try:
            num = int(num_str)
        except ValueError:
            return old_name
            
        new_num = num + increment
        if new_num < 0:
            new_num = 0
            
        # Preserve original zero-padding width
        width = len(num_str)
        new_episode_part = f"{prefix}{str(new_num).zfill(width)}"
        
        # Splicing the string using the match object's exact positional spans ensures
        # we don't accidentally replace earlier identical sequences, keeping the rest unchanged.
        start, end = match.span()
        new_name = old_name[:start] + season_part + new_episode_part + old_name[end:]
        return new_name

    def update_preview(self):
        """Update the list view with preview file names based on current input and selection."""
        try:
            increment = self.increment_var.get()
        except tk.TclError:
            increment = 0 # Fallback for invalid input state during typing
            
        selected_ids = self.tree.selection()
        
        for data in self.files_data:
            item_id = data["id"]
            if item_id in selected_ids:
                new_name = self.calculate_new_name(data["old_name"], data["match"], increment)
                if new_name != data["old_name"] and increment != 0:
                    status = "Pending"
                else:
                    status = "No Change"
            else:
                new_name = ""
                status = "Skipped"
                
            data["new_name"] = new_name
            
            # Update values in treeview explicitly
            curr_values = self.tree.item(item_id, "values")
            self.tree.item(item_id, values=(curr_values[0], curr_values[1], new_name, status))
            
        self.status_var.set(f"Selected {len(selected_ids)} / {len(self.files_data)} items.")

    def execute_rename(self):
        """Loops gracefully to apply the rename, handles conflicts, and supports dry running."""
        selected_ids = self.tree.selection()
        if not selected_ids:
            messagebox.showinfo("Wait", "Please select items to rename from the list.")
            return
            
        try:
            increment = self.increment_var.get()
        except tk.TclError:
            messagebox.showerror("Error", "Check your increment input.")
            return
            
        if increment == 0:
            messagebox.showinfo("Info", "Increment is 0. Operation has been aborted.")
            return

        is_dry_run = self.dry_run_var.get()
        
        operations = []
        for data in self.files_data:
            if data["id"] in selected_ids:
                if data["new_name"] and data["new_name"] != data["old_name"]:
                    old_path = data["full_path"]
                    new_path = os.path.join(data["root"], data["new_name"])
                    operations.append((old_path, new_path, data["id"]))
                    
        if not operations:
            messagebox.showinfo("Info", "No valid matching operations identified.")
            return

        if not is_dry_run:
            msg = f"You are confirming renaming {len(operations)} files.\nEnsure your files are not open in media players.\nProceed?"
            if not messagebox.askyesno("Confirm", msg):
                return

        success_count = 0
        current_undo_stack = []
        conflict_action = None
        auto_renamed_files = [] # Track files that were auto-renamed

        for old_path, new_path, item_id in operations:
            if old_path == new_path:
                continue

            target_path = new_path
            is_auto_renamed = False
            
            # Preempt conflict handling if target already exists and NOT running Dry run
            if os.path.exists(target_path) and not is_dry_run:
                if conflict_action is None:
                    action = self.ask_conflict_resolution(os.path.basename(target_path))
                    if action == "cancel":
                        logging.warning("Rename operation aborted by user due to conflict.")
                        break
                    if action in ["skip_all", "overwrite_all", "auto_all"]:
                        conflict_action = action
                    else:
                        conflict_action = None
                        
                    current_action = action.replace("_all", "")
                else:
                    current_action = conflict_action.replace("_all", "")
                    
                if current_action == "skip":
                    values = self.tree.item(item_id, "values")
                    self.tree.item(item_id, values=(values[0], values[1], os.path.basename(target_path), "Conflict-Skip"))
                    logging.info(f"Skipped conflict existing target: {target_path}")
                    continue
                elif current_action == "auto":
                    base, ext = os.path.splitext(target_path)
                    counter = 1
                    while os.path.exists(f"{base}_{counter}{ext}"):
                        counter += 1
                    target_path = f"{base}_{counter}{ext}"
                    is_auto_renamed = True
                elif current_action == "overwrite":
                    pass
                    
            if is_dry_run:
                values = self.tree.item(item_id, "values")
                self.tree.item(item_id, values=(values[0], values[1], os.path.basename(target_path), "[DRY RUN] OK"))
                logging.info(f"DRY RUN: Evaluated '{old_path}' to '{target_path}'")
                success_count += 1
            else:
                try:
                    os.replace(old_path, target_path) # Automatically overwrites safely across OSes
                    success_count += 1
                    current_undo_stack.append((target_path, old_path))
                    
                    if is_auto_renamed:
                        auto_renamed_files.append((target_path, new_path, item_id))
                        
                    logging.info(f"RENAMED: '{old_path}' -> '{target_path}'")
                    values = self.tree.item(item_id, "values")
                    self.tree.item(item_id, values=(values[0], values[1], os.path.basename(target_path), "Success"))
                    
                    # Ensure underlying item meta updates without total rescan to protect state
                    for d in self.files_data:
                        if d["id"] == item_id:
                            d["old_name"] = os.path.basename(target_path)
                            d["full_path"] = target_path
                            break
                            
                except Exception as e:
                    logging.error(f"FAILED renaming: '{old_path}' -> '{target_path}'. Reason: {e}")
                    values = self.tree.item(item_id, "values")
                    self.tree.item(item_id, values=(values[0], values[1], os.path.basename(target_path), "Error: Failed"))

        # Second pass: Remove appended numbers from auto-renamed files if the target name is now available
        if not is_dry_run and auto_renamed_files:
            for temp_target, original_target, item_id in auto_renamed_files:
                if not os.path.exists(original_target):
                    try:
                        os.replace(temp_target, original_target)
                        logging.info(f"POST-BATCH RENAME: '{temp_target}' -> '{original_target}'")
                        
                        # Update undo stack: replace temp_target with original_target
                        for i, (curr, orig) in enumerate(current_undo_stack):
                            if curr == temp_target:
                                current_undo_stack[i] = (original_target, orig)
                                break
                                
                        # Update tree view and state again
                        values = self.tree.item(item_id, "values")
                        self.tree.item(item_id, values=(values[0], values[1], os.path.basename(original_target), "Success"))
                        
                        for d in self.files_data:
                            if d["id"] == item_id:
                                d["old_name"] = os.path.basename(original_target)
                                d["full_path"] = original_target
                                break
                    except Exception as e:
                        logging.error(f"POST-BATCH RENAME FAILED: '{temp_target}' -> '{original_target}'. Reason: {e}")

        if not is_dry_run and current_undo_stack:
            self.last_operation = current_undo_stack
            self.undo_btn.config(state=tk.NORMAL)
            
        msg = f"Task completed.\nFiles Modified: {success_count}."
        if is_dry_run:
            messagebox.showinfo("Dry Run", msg + "\n(Logs checked. Nothing physical changed.)")
        else:
            messagebox.showinfo("Complete", msg)
            if success_count > 0:
                self.scan_folder()

    def ask_conflict_resolution(self, filename):
        """Launch custom modal for resolving name clashes individually or batching rule."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Resolve Conflict")
        dialog.geometry("380x280")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"File already exists:\n{filename}", justify=tk.CENTER, padding=15).pack()
        
        result = tk.StringVar(value="skip")
        
        def commit(val):
            result.set(val)
            dialog.destroy()
            
        ttk.Button(dialog, text="Skip This File", command=lambda: commit("skip")).pack(fill=tk.X, padx=25, pady=2)
        ttk.Button(dialog, text="Skip All Existing", command=lambda: commit("skip_all")).pack(fill=tk.X, padx=25, pady=2)
        ttk.Button(dialog, text="Auto-Rename appending _1", command=lambda: commit("auto")).pack(fill=tk.X, padx=25, pady=2)
        ttk.Button(dialog, text="Auto-Rename All", command=lambda: commit("auto_all")).pack(fill=tk.X, padx=25, pady=2)
        ttk.Button(dialog, text="Force Overwrite", command=lambda: commit("overwrite")).pack(fill=tk.X, padx=25, pady=2)
        ttk.Button(dialog, text="Halt Entire Progress", command=lambda: commit("cancel")).pack(fill=tk.X, padx=25, pady=10)
        
        self.root.wait_window(dialog)
        return result.get()

    def undo_rename(self):
        """Recover all names transformed in the last single execute invocation."""
        if not self.last_operation:
            return
            
        success = 0
        for current_path, original_path in reversed(self.last_operation):
            try:
                if os.path.exists(current_path):
                    os.replace(current_path, original_path)
                    logging.info(f"UNDO OPERATION: '{current_path}' to '{original_path}'")
                    success += 1
            except Exception as e:
                logging.error(f"UNDO FAILED: '{current_path}' to '{original_path}'. Reason: {e}")
                
        messagebox.showinfo("Reversed", f"Reverted changes successfully to {success} out of {len(self.last_operation)} files.")
        self.last_operation = []
        self.undo_btn.config(state=tk.DISABLED)
        self.scan_folder()

if __name__ == "__main__":
    root = tk.Tk()
    app = EpisodeRenamerApp(root)
    root.mainloop()
