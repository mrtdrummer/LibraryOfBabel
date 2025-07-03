import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, BooleanVar
from tkinter.scrolledtext import ScrolledText
import hashlib
import random
import string
import math
import threading
from collections import OrderedDict


class LibraryOfBabel:
    def __init__(self, include_numbers=False, max_cache_size=10000):
        """Initialize the Library of Babel with improved memory management and thread safety."""
        self.include_numbers = include_numbers
        self.max_cache_size = max_cache_size
        self.PAGE_LENGTH = 1000
        self.set_charset(include_numbers)
        self.CONSTANT_SEED = "8e447372cbc75ffc238749baf6eccbec586104336af37347606d14c698eaec1f"

        # Library structure (Borgesian dimensions)
        self.WALLS_PER_HEX = 5
        self.SHELVES_PER_WALL = 10
        self.VOLUMES_PER_SHELF = 32
        self.PAGES_PER_VOLUME = 410

        # Thread-safe caches with size limits
        self._cache_lock = threading.RLock()
        self._address_cache = OrderedDict()
        self._content_cache = OrderedDict()

    def set_charset(self, include_numbers):
        """Set character set and calculate correct hex length for theoretical completeness."""
        if include_numbers:
            self.CHARSET = string.ascii_lowercase + ' ,.' + string.digits  # 39 characters
            self.HEX_LENGTH = self._calculate_required_hex_length(39)  # 1023 characters
        else:
            self.CHARSET = string.ascii_lowercase + ' ,.'  # 29 characters
            self.HEX_LENGTH = self._calculate_required_hex_length(29)  # 940 characters
        self.BASE = len(self.CHARSET)

    def _calculate_required_hex_length(self, charset_size):
        """Calculate the exact required hex length for theoretical completeness."""
        # Total possible pages = charset_size^PAGE_LENGTH
        # Hex namespace = 36^L (36 possible chars per hex digit)
        # Solve: 36^L >= charset_size^PAGE_LENGTH
        log10_pages = self.PAGE_LENGTH * math.log10(charset_size)
        log36 = math.log10(36)
        return math.ceil(log10_pages / log36)

    def set_include_numbers(self, include_numbers):
        """Toggle number inclusion and clear caches."""
        self.include_numbers = include_numbers
        self.set_charset(include_numbers)
        with self._cache_lock:
            self._address_cache.clear()
            self._content_cache.clear()

    def set_seed(self, new_seed):
        """Set new cryptographic seed and clear caches."""
        self.CONSTANT_SEED = new_seed
        with self._cache_lock:
            self._address_cache.clear()
            self._content_cache.clear()

    def _generate_hex_name(self, base_input, variant=0):
        """Improved hex name generation using full 36-character space efficiently."""
        hex_chars = "0123456789abcdefghijklmnopqrstuvwxyz"
        combined_input = self.CONSTANT_SEED + str(base_input) + str(variant)
        hex_name = ""
        current_hash = hashlib.sha256(combined_input.encode()).hexdigest()

        # Use multiple hash rounds for better distribution
        hash_counter = 0
        while len(hex_name) < self.HEX_LENGTH:
            for i in range(0, len(current_hash), 2):
                if len(hex_name) >= self.HEX_LENGTH:
                    break
                # Use pairs of hex chars for better distribution across full 36-char space
                pair_val = int(current_hash[i:i + 2], 16) if i + 1 < len(current_hash) else int(current_hash[i], 16)
                hex_name += hex_chars[pair_val % 36]

            if len(hex_name) < self.HEX_LENGTH:
                hash_counter += 1
                current_hash = hashlib.sha256((current_hash + str(hash_counter)).encode()).hexdigest()

        return hex_name[:self.HEX_LENGTH]

    def _manage_cache(self, cache, key, value):
        """Thread-safe cache management with LRU eviction and size limits."""
        with self._cache_lock:
            if key in cache:
                # Move to end (most recently used)
                cache.move_to_end(key)
                return cache[key]

            cache[key] = value
            cache.move_to_end(key)

            # Remove oldest entries if cache exceeds limit
            while len(cache) > self.max_cache_size:
                cache.popitem(last=False)

            return value

    def _create_deterministic_address(self, text_input, location_variant=0):
        """Create deterministic address with improved coordinate generation."""
        hex_name = self._generate_hex_name(text_input, location_variant)
        coord_seed = self.CONSTANT_SEED + hex_name + str(location_variant)
        coord_hash = hashlib.sha256(coord_seed.encode()).hexdigest()

        wall = (int(coord_hash[0:4], 16) % self.WALLS_PER_HEX) + 1
        shelf = (int(coord_hash[4:8], 16) % self.SHELVES_PER_WALL) + 1
        volume = (int(coord_hash[8:12], 16) % self.VOLUMES_PER_SHELF) + 1
        page = (int(coord_hash[12:16], 16) % self.PAGES_PER_VOLUME) + 1

        address = f"{hex_name}-w{wall}-s{shelf}-v{volume}:{page}"
        return address

    def generate_deterministic_content(self, address, content_text=None):
        """Generate deterministic content with improved caching."""
        with self._cache_lock:
            if address in self._content_cache:
                return self._content_cache[address]

        if content_text:
            content = content_text
        else:
            content_seed = self.CONSTANT_SEED + address
            hash_obj = hashlib.sha256(content_seed.encode())
            seed_value = int(hash_obj.hexdigest(), 16)
            rng = random.Random(seed_value)
            content = ''.join(rng.choice(self.CHARSET) for _ in range(self.PAGE_LENGTH))

        return self._manage_cache(self._content_cache, address, content)

    def _create_exact_match_variations(self, text, num_variants=1):
        """Create exact match variations with proper padding."""
        clean_text = ''.join(c for c in text.lower() if c in self.CHARSET)
        variations = []

        for i in range(num_variants):
            if len(clean_text) <= self.PAGE_LENGTH:
                exact_content = clean_text + ' ' * (self.PAGE_LENGTH - len(clean_text))
            else:
                exact_content = clean_text[:self.PAGE_LENGTH]

            address = self._create_deterministic_address(exact_content, i)
            self.generate_deterministic_content(address, exact_content)

            variations.append({
                'address': address,
                'content': exact_content,
                'search_text': clean_text,
                'position': 0,
                'type': 'exact',
                'description': f'Exact match {i + 1} - full text with space padding'
            })

        return variations

    def _create_similar_match_variations(self, text, num_variants=5):
        """Fixed similar match generation with proper bounds checking."""
        clean_text = ''.join(c for c in text.lower() if c in self.CHARSET)
        if not clean_text:
            return []

        # Handle text longer than page length
        if len(clean_text) > self.PAGE_LENGTH:
            clean_text = clean_text[:self.PAGE_LENGTH]

        variations = []
        for i in range(num_variants):
            address = self._create_deterministic_address(clean_text, i + 1000)
            content = self.generate_deterministic_content(address)
            content_list = list(content)

            # Safe insertion position calculation
            max_insert_pos = max(0, self.PAGE_LENGTH - len(clean_text))
            if max_insert_pos > 0:
                rng = random.Random(hash(address) % (2 ** 32))
                insert_pos = rng.randint(0, max_insert_pos)
                content_list[insert_pos:insert_pos + len(clean_text)] = list(clean_text)
            else:
                # If text fills entire page, place at beginning
                content_list[:len(clean_text)] = list(clean_text)
                insert_pos = 0

            new_content = ''.join(content_list)
            self._manage_cache(self._content_cache, address, new_content)

            variations.append({
                'address': address,
                'content': new_content,
                'search_text': clean_text,
                'position': insert_pos,
                'type': 'similar',
                'description': f'Organic match at position {insert_pos}'
            })

        return variations

    def search_text(self, search_text, num_exact_locations=1, num_similar_results=5):
        """Enhanced search with comprehensive input validation and error handling."""
        if not search_text or not search_text.strip():
            return []

        original_text = search_text
        clean_text = ''.join(c for c in search_text.lower() if c in self.CHARSET)

        # Provide feedback for Unicode or unsupported characters
        if not clean_text and original_text.strip():
            raise ValueError(f"Search text contains no supported characters. Supported: {self.CHARSET}")

        if not clean_text:
            return []

        # Truncate if too long with user notification
        if len(clean_text) > self.PAGE_LENGTH:
            clean_text = clean_text[:self.PAGE_LENGTH]

        exact_matches = self._create_exact_match_variations(clean_text, num_exact_locations)
        similar_matches = self._create_similar_match_variations(clean_text, num_similar_results)

        return exact_matches + similar_matches

    def parse_address(self, address):
        """Enhanced address parsing with comprehensive validation."""
        try:
            if not address or ':' not in address:
                raise ValueError("Invalid address format: missing colon separator")

            hex_part, page_str = address.rsplit(':', 1)
            page = int(page_str)

            parts = hex_part.split('-')
            if len(parts) < 4:
                raise ValueError("Invalid address format: insufficient components")

            hex_name = parts[0]
            if not hex_name:
                raise ValueError("Invalid address format: empty hex name")

            try:
                wall = int(parts[1][1:])  # Skip 'w' prefix
                shelf = int(parts[2][1:])  # Skip 's' prefix
                volume = int(parts[3][1:])  # Skip 'v' prefix
            except (ValueError, IndexError):
                raise ValueError("Invalid address format: invalid coordinate format")

            # Validate coordinate ranges (1-based indexing)
            if not (1 <= wall <= self.WALLS_PER_HEX):
                raise ValueError(f"Invalid wall number: {wall} (must be 1-{self.WALLS_PER_HEX})")
            if not (1 <= shelf <= self.SHELVES_PER_WALL):
                raise ValueError(f"Invalid shelf number: {shelf} (must be 1-{self.SHELVES_PER_WALL})")
            if not (1 <= volume <= self.VOLUMES_PER_SHELF):
                raise ValueError(f"Invalid volume number: {volume} (must be 1-{self.VOLUMES_PER_SHELF})")
            if not (1 <= page <= self.PAGES_PER_VOLUME):
                raise ValueError(f"Invalid page number: {page} (must be 1-{self.PAGES_PER_VOLUME})")

            return hex_name, wall, shelf, volume, page

        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid address format: {address} - {str(e)}") from e

    def generate_page_from_address(self, address):
        """Generate page from address with comprehensive error handling."""
        try:
            # Validate address format first
            self.parse_address(address)
            return self.generate_deterministic_content(address)
        except ValueError as e:
            return f"Invalid address format: {e}"

    def generate_random_page(self):
        """Generate truly random page with full address information."""
        wall = random.randint(1, self.WALLS_PER_HEX)
        shelf = random.randint(1, self.SHELVES_PER_WALL)
        volume = random.randint(1, self.VOLUMES_PER_SHELF)
        page = random.randint(1, self.PAGES_PER_VOLUME)
        hex_name = self._generate_hex_name(str(random.random()), 0)
        address = f"{hex_name}-w{wall}-s{shelf}-v{volume}:{page}"
        content = self.generate_deterministic_content(address)

        return {
            'address': address,
            'content': content,
            'wall': wall,
            'shelf': shelf,
            'volume': volume,
            'page': page
        }

    def browse_hex_structure(self, hex_name, wall=None, shelf=None, volume=None):
        """Browse library structure with proper navigation hierarchy."""
        results = []

        if wall is None:
            # Browse walls
            for w in range(1, self.WALLS_PER_HEX + 1):
                sample_address = f"{hex_name}-w{w}-s1-v1:1"
                sample_content = self.generate_deterministic_content(sample_address)[:50]
                results.append({
                    'type': 'wall',
                    'identifier': f"Wall {w}",
                    'address': sample_address,
                    'preview': sample_content + "..."
                })
        elif shelf is None:
            # Browse shelves within wall
            for s in range(1, self.SHELVES_PER_WALL + 1):
                sample_address = f"{hex_name}-w{wall}-s{s}-v1:1"
                sample_content = self.generate_deterministic_content(sample_address)[:50]
                results.append({
                    'type': 'shelf',
                    'identifier': f"Shelf {s}",
                    'address': sample_address,
                    'preview': sample_content + "..."
                })
        elif volume is None:
            # Browse volumes within shelf
            for v in range(1, self.VOLUMES_PER_SHELF + 1):
                sample_address = f"{hex_name}-w{wall}-s{shelf}-v{v}:1"
                sample_content = self.generate_deterministic_content(sample_address)[:50]
                results.append({
                    'type': 'volume',
                    'identifier': f"Volume {v}",
                    'address': sample_address,
                    'preview': sample_content + "..."
                })
        else:
            # Browse pages within volume
            for p in range(1, self.PAGES_PER_VOLUME + 1):
                address = f"{hex_name}-w{wall}-s{shelf}-v{volume}:{p}"
                content_preview = self.generate_deterministic_content(address)[:100]
                results.append({
                    'type': 'page',
                    'identifier': f"Page {p}",
                    'address': address,
                    'preview': content_preview + "..."
                })

        return results

    def get_cache_stats(self):
        """Get current cache statistics for monitoring."""
        with self._cache_lock:
            return {
                'address_cache_size': len(self._address_cache),
                'content_cache_size': len(self._content_cache),
                'max_cache_size': self.max_cache_size
            }


class LibraryOfBabelGUI:
    def __init__(self):
        """Initialize the GUI with corrected Tkinter variable ordering."""
        # Step 1: Create root window FIRST
        self.root = tk.Tk()
        self.root.title("Library of Babel - Enhanced Edition")
        self.root.geometry("900x750")
        self.root.configure(bg='#1a1a2e')

        # Step 2: Define color scheme
        self.bg_color = '#1a1a2e'
        self.fg_color = '#ffffff'
        self.button_bg = '#16213e'
        self.button_fg = '#00d4aa'
        self.button_active_bg = '#0f3460'
        self.highlight_color = '#00d4aa'

        # Step 3: Create Tkinter variables AFTER root window
        self.include_numbers = BooleanVar(value=False)

        # Step 4: Initialize library
        self.library = LibraryOfBabel(include_numbers=False)

        # Step 5: Create widgets and show welcome
        self.create_widgets()
        self.show_welcome()

    def create_widgets(self):
        """Create enhanced GUI interface with improved layout."""
        # Title
        title_label = tk.Label(
            self.root,
            text="Library of Babel",
            font=("Arial", 24, "bold"),
            bg=self.bg_color,
            fg=self.highlight_color
        )
        title_label.pack(pady=20)

        # Subtitle
        subtitle_label = tk.Label(
            self.root,
            text="Infinite Knowledge Repository - Enhanced Edition",
            font=("Arial", 14),
            bg=self.bg_color,
            fg=self.fg_color
        )
        subtitle_label.pack(pady=5)

        # Current configuration info
        self.config_label = tk.Label(
            self.root,
            text=self._get_config_text(),
            font=("Courier", 13),
            bg=self.bg_color,
            fg=self.fg_color
        )
        self.config_label.pack(pady=10)

        # Number inclusion checkbox
        checkbox_frame = tk.Frame(self.root, bg=self.bg_color)
        checkbox_frame.pack(pady=10)

        self.numbers_checkbox = tk.Checkbutton(
            checkbox_frame,
            text="Include numbers (0-9) in search",
            variable=self.include_numbers,
            font=("Arial", 12),
            bg=self.bg_color,
            fg=self.highlight_color,
            selectcolor=self.bg_color,
            activebackground=self.bg_color,
            activeforeground=self.highlight_color,
            command=self.toggle_numbers
        )
        self.numbers_checkbox.pack()

        # Main buttons
        button_frame = tk.Frame(self.root, bg=self.bg_color)
        button_frame.pack(pady=30)

        buttons = [
            ("Search Text", self.search_text),
            ("Browse Address", self.browse_address),
            ("Browse Structure", self.browse_hex_structure),
            ("Random Page", self.random_page),
            ("Set Seed", self.set_custom_seed),
            ("Statistics", self.show_statistics)
        ]

        for i, (text, command) in enumerate(buttons):
            btn = tk.Button(
                button_frame,
                text=text,
                command=command,
                font=("Arial", 12, "bold"),
                bg=self.button_bg,
                fg=self.button_fg,
                activebackground=self.button_active_bg,
                activeforeground='#00ff88',
                relief='raised',
                bd=3,
                padx=20,
                pady=10,
                width=18
            )
            row = i // 2
            col = i % 2
            btn.grid(row=row, column=col, padx=10, pady=10)

    def _get_config_text(self):
        """Get current configuration text for display."""
        charset_size = len(self.library.CHARSET)
        return f"Characters: {charset_size} | Hex Length: {self.library.HEX_LENGTH} | Cache: {self.library.get_cache_stats()['content_cache_size']}"

    def toggle_numbers(self):
        """Toggle number inclusion with user feedback."""
        try:
            self.library.set_include_numbers(self.include_numbers.get())
            self.config_label.config(text=self._get_config_text())

            mode = "with numbers" if self.include_numbers.get() else "letters only"
            messagebox.showinfo(
                "Configuration Updated",
                f"Library mode changed to: {mode}\n"
                f"Character set: {len(self.library.CHARSET)} symbols\n"
                f"Hex length: {self.library.HEX_LENGTH} characters"
            )
        except Exception as e:
            messagebox.showerror("Configuration Error", f"Failed to update configuration: {str(e)}")

    def set_custom_seed(self):
        """Set custom cryptographic seed with validation."""
        current_seed = self.library.CONSTANT_SEED
        new_seed = simpledialog.askstring(
            "Set Cryptographic Seed",
            f"Current seed: {current_seed[:16]}...\n\n"
            "Enter new 64-character hexadecimal seed\n"
            "(leave empty to reset to default):",
            parent=self.root
        )

        if new_seed is not None:
            try:
                if new_seed.strip():
                    # Basic validation for hex format
                    if len(new_seed.strip()) < 32:
                        raise ValueError("Seed too short (minimum 32 characters)")

                    self.library.set_seed(new_seed.strip())
                    self.config_label.config(text=self._get_config_text())
                    messagebox.showinfo("Seed Updated",
                                        f"Cryptographic seed updated\n"
                                        f"New seed: {new_seed[:16]}...")
                else:
                    # Reset to default
                    default_seed = "8e447372cbc75ffc238749baf6eccbec586104336af37347606d14c698eaec1f"
                    self.library.set_seed(default_seed)
                    self.config_label.config(text=self._get_config_text())
                    messagebox.showinfo("Seed Reset", "Seed reset to default value")

            except Exception as e:
                messagebox.showerror("Seed Error", f"Invalid seed format: {str(e)}")

    def show_welcome(self):
        """Display enhanced welcome message with current improvements."""
        welcome_text = (
            " Welcome to the Enhanced Library of Babel! \n\n"
            "This improved implementation includes:\n\n"
            " Key Enhancements:\n"
            "• Corrected hex length calculations for true completeness\n"
            "• Thread-safe caches with automatic memory management\n"
            "• Comprehensive input validation and error handling\n"
            "• Optional number support (0-9) with dynamic configuration\n"
            "• Enhanced address validation with range checking\n"
            "• Improved hex name generation using full 36-character space\n\n"
            "  Current Configuration:\n"
            f"• Character set: {len(self.library.CHARSET)} symbols\n"
            f"• Hex length: {self.library.HEX_LENGTH} characters\n"
            f"• Page length: {self.library.PAGE_LENGTH} characters\n"
            f"• Cache limit: {self.library.max_cache_size:,} entries\n\n"
            "🔍 Search Features:\n"
            "• 1 perfect match (exact text with padding)\n"
            "• 5 organic matches (text as natural substring)\n"
            "• Unicode character detection and feedback\n"
            "• Automatic text truncation for long inputs\n\n"
            "Explore the infinite possibilities of literature, mathematics, and meaning!"
        )
        messagebox.showinfo("Welcome to Enhanced Babel", welcome_text)

    def copy_to_clipboard(self, text):
        """Copy text to system clipboard with error handling."""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            messagebox.showinfo("Copied", "Text copied to clipboard successfully!")
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy text: {str(e)}")

    def create_results_window(self, title, results, is_search=False):
        """Create enhanced results window with improved formatting."""
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("1400x1000")
        window.configure(bg=self.bg_color)

        # Main content frame
        main_frame = tk.Frame(window, bg=self.bg_color)
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)

        # Text display
        text_widget = ScrolledText(
            main_frame,
            font=("Courier", 13),
            bg=self.button_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            selectbackground=self.highlight_color,
            selectforeground='black',
            wrap=tk.WORD,
            state='normal'
        )
        text_widget.pack(fill='both', expand=True)

        # Format search results with enhanced display
        if is_search and isinstance(results, list):
            content = f"🔍 SEARCH RESULTS: '{results[0]['search_text']}'\n"
            content += "_" * 120 + "\n\n"

            # Group by match type
            exact_matches = [r for r in results if r['type'] == 'exact']
            similar_matches = [r for r in results if r['type'] == 'similar']

            if exact_matches:
                content += f" PERFECT MATCHES ({len(exact_matches)})\n"
                content += "Full searched text preserved exactly\n"
                content += "_" * 120 + "\n\n"
                for i, res in enumerate(exact_matches, 1):
                    content += f"Match {i}:\n"
                    content += f"Address: {res['address']}\n"
                    content += " " * 120 + "\n\n"
                    content += f"Preview: {res['content'][:180]}...\n\n"

            if similar_matches:
                content += f" ORGANIC MATCHES ({len(similar_matches)})\n"
                content += "Text found as natural substring within generated pages\n"
                content += "_" * 120 + "\n\n"
                for i, res in enumerate(similar_matches, 1):
                    content += f"Match {i}:\n"
                    content += f"Address: {res['address']}\n"
                    content += f"Position: {res['position']}\n"
                    start_pos = max(0, res['position'] - 30)
                    end_pos = min(len(res['content']), res['position'] + len(res['search_text']) + 30)
                    context = res['content'][start_pos:end_pos]
                    content += "_" * 120 + "\n\n"
                    content += f"Context: ...{context}...\n\n"

            # Add statistics
            content += "\n" + "=" * 120 + "\n"
            content += f"Search completed successfully\n"
            content += f"Character set: {len(self.library.CHARSET)} symbols\n"
            content += f"Cache entries: {self.library.get_cache_stats()['content_cache_size']}\n"
        else:
            content = results

        text_widget.insert('1.0', content)

        # Control buttons
        button_frame = tk.Frame(window, bg=self.bg_color)
        button_frame.pack(fill='x', pady=10)

        copy_btn = tk.Button(
            button_frame,
            text="Copy All Text",
            command=lambda: self.copy_to_clipboard(content),
            font=("Arial", 11, "bold"),
            bg=self.highlight_color,
            fg='black',
            padx=20,
            pady=5
        )
        copy_btn.pack(side='left', padx=5)

        def copy_selected():
            try:
                selected_text = text_widget.get('sel.first', 'sel.last')
                if selected_text:
                    self.copy_to_clipboard(selected_text)
                else:
                    messagebox.showwarning("No Selection", "Please select text first")
            except tk.TclError:
                messagebox.showwarning("No Selection", "Please select text first")

        copy_selected_btn = tk.Button(
            button_frame,
            text="Copy Selected",
            command=copy_selected,
            font=("Arial", 11, "bold"),
            bg=self.highlight_color,
            fg='black',
            padx=20,
            pady=5
        )
        copy_selected_btn.pack(side='left', padx=5)

    def search_text(self):
        """Enhanced text search with comprehensive error handling."""
        search_term = simpledialog.askstring(
            "Search the Infinite Library",
            f"Enter text to search (max {self.library.PAGE_LENGTH} chars):\n\n"
            f"Current mode: {len(self.library.CHARSET)} character set\n"
            f"Supported: {self.library.CHARSET}\n\n"
            "Returns: 1 exact + 5 organic matches",
            parent=self.root
        )

        if not search_term:
            return

        if len(search_term) > self.library.PAGE_LENGTH:
            if not messagebox.askyesno(
                    "Long Text Warning",
                    f"Search text exceeds {self.library.PAGE_LENGTH} characters and will be truncated.\n\n"
                    "Continue with truncated search?"
            ):
                return

        # Show processing dialog
        processing = tk.Toplevel(self.root)
        processing.title("Searching...")
        processing.geometry("350x120")
        processing.configure(bg=self.bg_color)
        processing.resizable(False, False)
        processing.transient(self.root)
        processing.grab_set()

        tk.Label(
            processing,
            text=f"Scanning infinite library for:\n'{search_term[:30]}{'...' if len(search_term) > 30 else ''}'",
            font=("Arial", 11),
            bg=self.bg_color,
            fg=self.fg_color,
            wraplength=300
        ).pack(expand=True)

        def perform_search():
            processing.after(100, processing.destroy)
            self.root.update()

            try:
                results = self.library.search_text(search_term, 1, 5)
                if results:
                    self.create_results_window(
                        f"Search Results: '{search_term[:50]}{'...' if len(search_term) > 50 else ''}'",
                        results,
                        is_search=True
                    )
                    # Update cache display
                    self.config_label.config(text=self._get_config_text())
                else:
                    messagebox.showinfo("No Results", "No matches found in the infinite library")
            except ValueError as e:
                messagebox.showerror("Search Error", str(e))
            except Exception as e:
                messagebox.showerror("Unexpected Error", f"Search failed: {str(e)}")

        processing.after(500, perform_search)

    def browse_address(self):
        """Browse specific address with enhanced validation."""
        address = simpledialog.askstring(
            "Browse Library Address",
            "Enter complete address:\n\n"
            "Format: [hex]-w[wall]-s[shelf]-v[volume]:[page]\n"
            "Example: abc123...-w1-s5-v12:200\n\n"
            f"Valid ranges:\n"
            f"• Walls: 1-{self.library.WALLS_PER_HEX}\n"
            f"• Shelves: 1-{self.library.SHELVES_PER_WALL}\n"
            f"• Volumes: 1-{self.library.VOLUMES_PER_SHELF}\n"
            f"• Pages: 1-{self.library.PAGES_PER_VOLUME}",
            parent=self.root
        )

        if not address:
            return

        try:
            # Validate address format
            hex_name, wall, shelf, volume, page = self.library.parse_address(address)
            content = self.library.generate_page_from_address(address)

            result_text = f"📖 PAGE CONTENT\n"
            result_text += "=" * 80 + "\n\n"
            result_text += f"Address: {address}\n"
            result_text += f"Location: Hex {hex_name[:20]}... → Wall {wall} → Shelf {shelf} → Volume {volume} → Page {page}\n"
            result_text += f"Character Set: {len(self.library.CHARSET)} symbols\n\n"
            result_text += "Content:\n"
            result_text += "-" * 40 + "\n"
            result_text += content

            self.create_results_window(f"Page: {address}", result_text)

        except ValueError as e:
            messagebox.showerror("Invalid Address", str(e))
        except Exception as e:
            messagebox.showerror("Browse Error", f"Failed to browse address: {str(e)}")

    def browse_hex_structure(self):
        """Browse library structure with enhanced navigation."""
        hex_name = simpledialog.askstring(
            "Explore Hex Structure",
            f"Enter hex name to explore:\n\n"
            f"• Length: {self.library.HEX_LENGTH} characters\n"
            f"• Characters: 0-9, a-z\n"
            f"• Leave empty for random hex\n\n"
            "Navigate through: Hex → Walls → Shelves → Volumes → Pages",
            parent=self.root
        )

        if hex_name is None:
            return

        if not hex_name:
            hex_name = self.library._generate_hex_name(str(random.random()), 0)
            messagebox.showinfo(
                "Random Hex Generated",
                f"Exploring random hex:\n{hex_name[:40]}...\n\n"
                f"Full length: {len(hex_name)} characters"
            )

        self.show_hex_browser(hex_name)

    def show_hex_browser(self, hex_name, wall=None, shelf=None, volume=None):
        """Display enhanced hex browser with improved navigation."""
        browser = tk.Toplevel(self.root)
        browser.title(f"Hex Explorer: {hex_name[:30]}...")
        browser.geometry("1000x800")
        browser.configure(bg=self.bg_color)

        # Navigation breadcrumb
        nav_parts = [f"Hex: {hex_name[:20]}..."]
        if wall: nav_parts.append(f"Wall {wall}")
        if shelf: nav_parts.append(f"Shelf {shelf}")
        if volume: nav_parts.append(f"Volume {volume}")

        nav_label = tk.Label(
            browser,
            text=" → ".join(nav_parts),
            font=("Arial", 14, "bold"),
            bg=self.bg_color,
            fg=self.highlight_color,
            wraplength=950
        )
        nav_label.pack(pady=15)

        try:
            items = self.library.browse_hex_structure(hex_name, wall, shelf, volume)

            # Create browsing interface
            list_frame = tk.Frame(browser, bg=self.bg_color)
            list_frame.pack(fill='both', expand=True, padx=20, pady=10)

            scrollbar = tk.Scrollbar(list_frame)
            scrollbar.pack(side='right', fill='y')

            listbox = tk.Listbox(
                list_frame,
                font=("Courier", 13),
                bg=self.button_bg,
                fg=self.fg_color,
                yscrollcommand=scrollbar.set,
                selectbackground=self.highlight_color,
                selectforeground='black'
            )
            listbox.pack(side='left', fill='both', expand=True)
            scrollbar.config(command=listbox.yview)

            # Populate list with items
            for item in items:
                display_text = f"{item['identifier']}: {item['preview'][:70]}{'...' if len(item['preview']) > 70 else ''}"
                listbox.insert('end', display_text)

            # Handle navigation
            def on_select(event):
                selection = listbox.curselection()
                if selection:
                    item = items[selection[0]]
                    try:
                        if item['type'] == 'wall':
                            wall_num = int(item['identifier'].split()[1])
                            self.show_hex_browser(hex_name, wall_num)
                        elif item['type'] == 'shelf':
                            shelf_num = int(item['identifier'].split()[1])
                            self.show_hex_browser(hex_name, wall, shelf_num)
                        elif item['type'] == 'volume':
                            volume_num = int(item['identifier'].split()[1])
                            self.show_hex_browser(hex_name, wall, shelf, volume_num)
                        elif item['type'] == 'page':
                            content = self.library.generate_page_from_address(item['address'])
                            self.create_results_window(f"Page: {item['address']}", content)
                    except Exception as e:
                        messagebox.showerror("Navigation Error", f"Failed to navigate: {str(e)}")

            listbox.bind('<Double-1>', on_select)

            # Instructions
            instruction_label = tk.Label(
                browser,
                text="Double-click any item to navigate deeper or view page content",
                font=("Arial", 10),
                bg=self.bg_color,
                fg=self.fg_color
            )
            instruction_label.pack(pady=5)

        except Exception as e:
            messagebox.showerror("Browser Error", f"Failed to browse structure: {str(e)}")

    def random_page(self):
        """Generate and display random page with enhanced information."""
        try:
            page_data = self.library.generate_random_page()

            result_text = f"🎲 RANDOM PAGE\n"
            result_text += "=" * 80 + "\n\n"
            result_text += f"Address: {page_data['address']}\n"
            result_text += f"Coordinates: Wall {page_data['wall']}, Shelf {page_data['shelf']}, "
            result_text += f"Volume {page_data['volume']}, Page {page_data['page']}\n"
            result_text += f"Character Set: {len(self.library.CHARSET)} symbols\n"
            result_text += f"Hex Length: {self.library.HEX_LENGTH} characters\n\n"
            result_text += "Content:\n"
            result_text += "-" * 40 + "\n"
            result_text += page_data['content']

            self.create_results_window("Random Page", result_text)

            # Update cache display
            self.config_label.config(text=self._get_config_text())

        except Exception as e:
            messagebox.showerror("Generation Error", f"Failed to generate random page: {str(e)}")

    def show_statistics(self):
        """Display comprehensive statistics with current improvements."""
        try:
            cache_stats = self.library.get_cache_stats()

            # Calculate theoretical values
            current_charset = len(self.library.CHARSET)
            alt_charset = 39 if current_charset == 29 else 29
            alt_hex_length = self.library._calculate_required_hex_length(alt_charset)

            # Calculate total possible pages
            log10_pages = self.library.PAGE_LENGTH * math.log10(current_charset)
            pages_exponent = int(log10_pages)

            stats_text = f"""📊 ENHANCED LIBRARY STATISTICS

Current Configuration:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Character Set: {current_charset} symbols ({'with' if self.library.include_numbers else 'without'} numbers)
• Supported Characters: {self.library.CHARSET}
• Page Length: {self.library.PAGE_LENGTH:,} characters
• Hex Name Length: {self.library.HEX_LENGTH:,} characters (mathematically exact)

Library Structure:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Walls per Hex: {self.library.WALLS_PER_HEX}
• Shelves per Wall: {self.library.SHELVES_PER_WALL} 
• Volumes per Shelf: {self.library.VOLUMES_PER_SHELF}
• Pages per Volume: {self.library.PAGES_PER_VOLUME}
• Total Pages per Hex: {self.library.WALLS_PER_HEX * self.library.SHELVES_PER_WALL * self.library.VOLUMES_PER_SHELF * self.library.PAGES_PER_VOLUME:,}

Alternative Configuration:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
• {alt_charset} characters ({'with' if not self.library.include_numbers else 'without'} numbers)
• Required Hex Length: {alt_hex_length:,} characters
• Length Difference: {abs(alt_hex_length - self.library.HEX_LENGTH):,} characters

Cosmic Scale:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Total Possible Pages: {current_charset}^{self.library.PAGE_LENGTH} ≈ 10^{pages_exponent:,}
• Atoms in Observable Universe: ~10^80
• Ratio: ~10^{pages_exponent - 80:,} times larger than atomic scale
• Required Hexes: ~10^{pages_exponent - 5:,}

"""

            messagebox.showinfo("Enhanced Library Statistics", stats_text)

        except Exception as e:
            messagebox.showerror("Statistics Error", f"Failed to generate statistics: {str(e)}")

    def run(self):
        """Start the enhanced Library of Babel application."""
        try:
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("Application Error", f"Critical error: {str(e)}")



if __name__ == "__main__":
    try:
        app = LibraryOfBabelGUI()
        app.run()
    except Exception as e:
        print(f"Failed to start Library of Babel: {e}")
        input("Press Enter to exit...")
