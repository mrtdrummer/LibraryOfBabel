import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText
import hashlib
import random
import string
import time
import re


class LibraryOfBabel:
    def __init__(self):
        # Character set: 26 lowercase letters + space + comma + period
        self.CHARSET = string.ascii_lowercase + ' ,.'
        self.BASE = len(self.CHARSET)  # 29
        self.PAGE_LENGTH = 1000
        self.HEX_LENGTH = 120

        # Default constant seed value (example)
        self.CONSTANT_SEED = "8e447372cbc75ffc238749baf6eccbec586104336af37347606d14c698eaec1f"

        # Library structure with 1-based indexing
        self.WALLS_PER_HEX = 5
        self.SHELVES_PER_WALL = 10
        self.VOLUMES_PER_SHELF = 32
        self.PAGES_PER_VOLUME = 410

        # Global cache to ensure consistency
        self._address_cache = {}
        self._content_cache = {}

    def set_seed(self, new_seed):
        """Allow manual override of the constant seed"""
        self.CONSTANT_SEED = new_seed
        self._address_cache = {}
        self._content_cache = {}

    def char_to_num(self, char):
        """Convert character to number (0-28)"""
        if char in self.CHARSET:
            return self.CHARSET.index(char)
        return 0

    def num_to_char(self, num):
        """Convert number to character"""
        return self.CHARSET[num % self.BASE]

    def _generate_hex_name(self, base_input, variant=0):
        """Generate a consistent hex name of exactly 120 characters"""
        combined_input = self.CONSTANT_SEED + str(base_input) + str(variant)
        hex_chars = "0123456789abcdefghijklmnopqrstuvwxyz"
        hex_name = ""

        current_hash = hashlib.sha256(combined_input.encode()).hexdigest()

        while len(hex_name) < self.HEX_LENGTH:
            for char in current_hash:
                if len(hex_name) >= self.HEX_LENGTH:
                    break
                hex_name += hex_chars[int(char, 16) % 36]

            if len(hex_name) < self.HEX_LENGTH:
                current_hash = hashlib.sha256((current_hash + combined_input).encode()).hexdigest()

        return hex_name[:self.HEX_LENGTH]

    def _create_exact_match_variations(self, text, num_variants=3):
        """Create exact match variations with different space padding patterns"""
        clean_text = ''.join(c for c in text.lower() if c in self.CHARSET)
        variations = []

        for i in range(num_variants):
            # Create exact match with spaces filling the rest
            if len(clean_text) < self.PAGE_LENGTH:
                exact_content = clean_text + ' ' * (self.PAGE_LENGTH - len(clean_text))
            else:
                exact_content = clean_text[:self.PAGE_LENGTH]

            variations.append({
                'text': exact_content,
                'original': clean_text,
                'type': 'exact',
                'description': f'Exact match {i + 1} - full text with space padding'
            })

        return variations

    def _create_similar_match_variations(self, text, num_variants=5):
        """Create similar matches: exact text with end spaces or as substring"""
        clean_text = ''.join(c for c in text.lower() if c in self.CHARSET)
        variations = []

        # Set deterministic seed for consistent similar variations
        random.seed(hash(text + self.CONSTANT_SEED) % (2 ** 32))

        for i in range(num_variants):
            if i < 2:
                # Type 1: Exact text with additional spaces at different positions
                if i == 0:
                    # Spaces at the end
                    spaces_before = 0
                    spaces_after = min(10, self.PAGE_LENGTH - len(clean_text))
                else:
                    # Spaces at the beginning
                    spaces_before = min(5, self.PAGE_LENGTH - len(clean_text))
                    spaces_after = min(5, self.PAGE_LENGTH - len(clean_text) - spaces_before)

                content = ' ' * spaces_before + clean_text + ' ' * spaces_after
                if len(content) < self.PAGE_LENGTH:
                    content += ' ' * (self.PAGE_LENGTH - len(content))
                else:
                    content = content[:self.PAGE_LENGTH]

                variations.append({
                    'text': content,
                    'original': clean_text,
                    'type': 'similar_spaces',
                    'description': f'Exact text with additional spaces (variation {i + 1})'
                })

            else:
                # Type 2: Exact text as substring within longer coherent text
                # Generate prefix and suffix using deterministic method
                prefix_length = random.randint(10, min(100, (self.PAGE_LENGTH - len(clean_text)) // 2))
                suffix_length = self.PAGE_LENGTH - len(clean_text) - prefix_length

                # Generate meaningful-looking prefix and suffix
                prefix = self._generate_coherent_text(prefix_length, i)
                suffix = self._generate_coherent_text(suffix_length, i + 100)

                content = prefix + clean_text + suffix
                if len(content) > self.PAGE_LENGTH:
                    content = content[:self.PAGE_LENGTH]
                elif len(content) < self.PAGE_LENGTH:
                    content += ' ' * (self.PAGE_LENGTH - len(content))

                variations.append({
                    'text': content,
                    'original': clean_text,
                    'type': 'similar_substring',
                    'description': f'Exact text as substring within longer text (variation {i - 1})'
                })

        return variations

    def _generate_coherent_text(self, length, seed_modifier):
        """Generate somewhat coherent text for similar match contexts"""
        # Use common English patterns for more realistic context
        common_patterns = [
            "the quick brown fox jumps over the lazy dog",
            "once upon a time in a distant land",
            "it was the best of times it was the worst of times",
            "to be or not to be that is the question",
            "in the beginning was the word and the word was",
            "all that glitters is not gold but silver shines",
            "a journey of a thousand miles begins with a single step"
        ]

        random.seed(hash(str(seed_modifier) + self.CONSTANT_SEED) % (2 ** 32))
        pattern = random.choice(common_patterns)

        # Repeat and modify pattern to reach desired length
        text = ""
        while len(text) < length:
            remaining = length - len(text)
            if remaining >= len(pattern):
                text += pattern + " "
            else:
                text += pattern[:remaining]

        # Clean and ensure only valid characters
        clean_text = ''.join(c for c in text.lower() if c in self.CHARSET)
        return clean_text[:length]

    def _create_deterministic_address(self, text_input, location_variant=0):
        """Create a deterministic address for consistent results"""
        hex_name = self._generate_hex_name(text_input, location_variant)

        coord_seed = self.CONSTANT_SEED + hex_name + str(location_variant)
        coord_hash = hashlib.sha256(coord_seed.encode()).hexdigest()

        wall = (int(coord_hash[0:4], 16) % self.WALLS_PER_HEX) + 1
        shelf = (int(coord_hash[4:8], 16) % self.SHELVES_PER_WALL) + 1
        volume = (int(coord_hash[8:12], 16) % self.VOLUMES_PER_SHELF) + 1
        page = (int(coord_hash[12:16], 16) % self.PAGES_PER_VOLUME) + 1

        address = f"{hex_name}-w{wall}-s{shelf}-v{volume}:{page}"

        self._address_cache[address] = {
            'text': text_input,
            'location_variant': location_variant
        }

        return address

    def generate_deterministic_content(self, address, content_text=None):
        """Generate deterministic content for an address"""
        if address in self._content_cache:
            return self._content_cache[address]

        if content_text:
            # Use provided content directly
            result = content_text
        else:
            # Generate random content for non-search addresses
            content_seed = self.CONSTANT_SEED + address
            hash_obj = hashlib.sha256(content_seed.encode())
            seed_value = int(hash_obj.hexdigest(), 16)

            random.seed(seed_value)
            content = []
            for i in range(self.PAGE_LENGTH):
                content.append(self.CHARSET[random.randint(0, self.BASE - 1)])
            result = ''.join(content)

        self._content_cache[address] = result
        return result

    def parse_address(self, address):
        """Parse address string into components"""
        try:
            if ':' not in address:
                raise ValueError("Invalid address format")

            hex_part, page_str = address.rsplit(':', 1)
            page = int(page_str)

            parts = hex_part.split('-')
            if len(parts) < 4:
                raise ValueError("Invalid address format")

            hex_name = parts[0]
            wall = int(parts[1][1:])
            shelf = int(parts[2][1:])
            volume = int(parts[3][1:])

            return hex_name, wall, shelf, volume, page
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid address format: {address}")

    def search_text(self, search_text, num_exact_locations=3, num_similar_results=5):
        """Enhanced search with refined exact and similar matching"""
        if not search_text.strip():
            return []

        clean_text = ''.join(c for c in search_text.lower() if c in self.CHARSET)
        if not clean_text:
            return []

        results = []

        # Generate exact match variations
        exact_variations = self._create_exact_match_variations(clean_text, num_exact_locations)

        for i, variation in enumerate(exact_variations):
            address = self._create_deterministic_address(variation['text'], i)
            content = self.generate_deterministic_content(address, variation['text'])

            # Verify exact text is present at the beginning
            text_position = content.find(clean_text)

            results.append({
                'address': address,
                'content': content,
                'search_text': clean_text,
                'original_query': search_text,
                'position': text_position,
                'type': 'exact',
                'variation': i + 1,
                'description': variation['description']
            })

        # Generate similar match variations
        if num_similar_results > 0:
            similar_variations = self._create_similar_match_variations(clean_text, num_similar_results)

            for i, variation in enumerate(similar_variations):
                address = self._create_deterministic_address(variation['text'], i + num_exact_locations)
                content = self.generate_deterministic_content(address, variation['text'])

                # Find position of exact text within the similar match
                text_position = content.find(clean_text)

                results.append({
                    'address': address,
                    'content': content,
                    'search_text': clean_text,
                    'original_query': search_text,
                    'position': text_position,
                    'type': 'similar',
                    'variation': i + 1,
                    'description': variation['description'],
                    'similarity_type': variation['type']
                })

        return results

    def generate_page_from_address(self, address):
        """Generate page content from address"""
        try:
            if address in self._address_cache:
                cached_info = self._address_cache[address]
                return self.generate_deterministic_content(address, cached_info['text'])

            return self.generate_deterministic_content(address)

        except ValueError as e:
            return f"Invalid address format: {e}"

    def generate_random_page(self):
        """Generate a random page"""
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
        """Browse hex structure with consistent addressing"""
        results = []

        if wall is None:
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


# GUI Implementation with Enhanced Search Display
class LibraryOfBabelGUI:
    def __init__(self):
        self.library = LibraryOfBabel()
        self.root = tk.Tk()
        self.root.title("Library of Babel")
        self.root.geometry("900x700")
        self.root.configure(bg='#1a1a2e')

        self.bg_color = '#1a1a2e'
        self.fg_color = '#ffffff'
        self.button_bg = '#16213e'
        self.button_fg = '#00d4aa'
        self.button_active_bg = '#0f3460'
        self.highlight_color = '#00d4aa'

        self.create_widgets()
        self.show_welcome()

    def create_widgets(self):
        """Create GUI widgets"""
        title_label = tk.Label(
            self.root,
            text="Library of Babel",
            font=("Arial", 24, "bold"),
            bg=self.bg_color,
            fg=self.highlight_color
        )
        title_label.pack(pady=20)

        subtitle_label = tk.Label(
            self.root,
            text="Enhanced exact and similar text matching",
            font=("Arial", 12),
            bg=self.bg_color,
            fg=self.fg_color
        )
        subtitle_label.pack(pady=10)

        self.seed_label = tk.Label(
            self.root,
            text=f"Current Seed: {self.library.CONSTANT_SEED[:16]}...",
            font=("Courier", 10),
            bg=self.bg_color,
            fg=self.fg_color
        )
        self.seed_label.pack(pady=5)

        button_frame = tk.Frame(self.root, bg=self.bg_color)
        button_frame.pack(pady=30)

        buttons = [
            ("Search Text", self.search_text),
            ("Browse Address", self.browse_address),
            ("Browse Hex Structure", self.browse_hex_structure),
            ("Random Page", self.random_page),
            ("Set Custom Seed", self.set_custom_seed),
            ("Library Statistics", self.show_statistics)
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
                width=20
            )
            row = i // 2
            col = i % 2
            btn.grid(row=row, column=col, padx=10, pady=10)

    def set_custom_seed(self):
        """Allow user to set custom seed"""
        new_seed = simpledialog.askstring(
            "Set Custom Seed",
            f"Enter new seed value (current: {self.library.CONSTANT_SEED[:16]}...):\n\nLeave empty to reset to default.",
            parent=self.root
        )

        if new_seed is not None:
            if new_seed.strip():
                self.library.set_seed(new_seed.strip())
                self.seed_label.config(text=f"Current Seed: {self.library.CONSTANT_SEED[:16]}...")
                messagebox.showinfo("Seed Updated", f"Seed updated to: {new_seed[:16]}...")
            else:
                self.library.set_seed("8e447372cbc75ffc238749baf6eccbec586104336af37347606d14c698eaec1f")
                self.seed_label.config(text=f"Current Seed: {self.library.CONSTANT_SEED[:16]}...")
                messagebox.showinfo("Seed Reset", "Seed reset to default value.")

    def show_welcome(self):
        """Show welcome dialog"""
        welcome_text = """Welcome to the Library of Babel!

Enhanced search functionality with precise text matching:

EXACT MATCHES:
• Full searched text appears exactly as entered
• Text is padded with spaces to fill page length
• Perfect character-level accuracy maintained

SIMILAR MATCHES:
• Exact text with additional spaces at ends
• Exact text as substring within longer passages
• All variations preserve the original search term

This ensures maximum precision in search results while
maintaining the infinite library concept."""

        messagebox.showinfo("Welcome", welcome_text)

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        messagebox.showinfo("Copied", "Text copied to clipboard!")

    def create_results_window(self, title, results, is_search=False):
        """Create enhanced results window with detailed search information"""
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("1000x800")
        window.configure(bg=self.bg_color)

        main_frame = tk.Frame(window, bg=self.bg_color)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        text_widget = ScrolledText(
            main_frame,
            font=("Courier", 10),
            bg=self.button_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            selectbackground=self.highlight_color,
            selectforeground='black',
            wrap=tk.WORD,
            state='normal'
        )
        text_widget.pack(fill='both', expand=True)

        if is_search and isinstance(results, list):
            content = f"REFINED SEARCH RESULTS ({len(results)} locations found)\n"
            content += "=" * 70 + "\n\n"

            exact_results = [r for r in results if r['type'] == 'exact']
            similar_results = [r for r in results if r['type'] == 'similar']

            if exact_results:
                content += f"EXACT MATCHES ({len(exact_results)} locations):\n"
                content += "Full searched text present exactly as entered\n"
                content += "-" * 50 + "\n\n"

                for result in exact_results:
                    content += f"Exact Match {result['variation']}:\n"
                    content += f"Description: {result['description']}\n"
                    content += f"Address: {result['address']}\n"
                    content += f"Text Position: {result['position']}\n"
                    content += f"Content Preview:\n{result['content'][:200]}...\n\n"
                    content += "~" * 60 + "\n\n"

            if similar_results:
                content += f"SIMILAR MATCHES ({len(similar_results)} found):\n"
                content += "Exact text with spaces or as substring\n"
                content += "-" * 50 + "\n\n"

                for result in similar_results:
                    content += f"Similar Match {result['variation']}:\n"
                    content += f"Type: {result['description']}\n"
                    content += f"Address: {result['address']}\n"
                    content += f"Text Position: {result['position']}\n"
                    content += f"Content Preview:\n{result['content'][:200]}...\n\n"
                    content += "~" * 60 + "\n\n"
        else:
            content = results

        text_widget.insert('1.0', content)

        def select_all(event):
            text_widget.tag_add('sel', '1.0', 'end')
            return 'break'

        text_widget.bind('<Control-a>', select_all)
        text_widget.bind('<Control-A>', select_all)

        button_frame = tk.Frame(window, bg=self.bg_color)
        button_frame.pack(fill='x', pady=10)

        copy_all_btn = tk.Button(
            button_frame,
            text="Copy All Text",
            command=lambda: self.copy_to_clipboard(content),
            font=("Arial", 10, "bold"),
            bg=self.highlight_color,
            fg='black',
            relief='raised',
            bd=2,
            padx=20
        )
        copy_all_btn.pack(side='left', padx=5)

        def copy_selected():
            try:
                selected_text = text_widget.get('sel.first', 'sel.last')
                if selected_text:
                    self.copy_to_clipboard(selected_text)
                else:
                    messagebox.showwarning("No Selection", "Please select text first.")
            except tk.TclError:
                messagebox.showwarning("No Selection", "Please select text first.")

        copy_selected_btn = tk.Button(
            button_frame,
            text="Copy Selected Text",
            command=copy_selected,
            font=("Arial", 10, "bold"),
            bg=self.highlight_color,
            fg='black',
            relief='raised',
            bd=2,
            padx=20
        )
        copy_selected_btn.pack(side='left', padx=5)

    def search_text(self):
        """Enhanced search with refined matching"""
        search_term = simpledialog.askstring(
            "Refined Text Search",
            "Enter text to search for (up to 1000 characters):\n\nEXACT MATCHES: Full text preserved exactly\nSIMILAR MATCHES: Exact text with spaces or as substring",
            parent=self.root
        )

        if not search_term:
            return

        if len(search_term) > 1000:
            messagebox.showwarning("Text Too Long", "Search text limited to 1000 characters.")
            return

        self.show_processing("Performing refined search...")

        try:
            results = self.library.search_text(
                search_term,
                num_exact_locations=3,
                num_similar_results=5
            )

            if results:
                self.create_results_window(
                    f"Refined Search Results - '{search_term}'",
                    results,
                    is_search=True
                )
            else:
                messagebox.showinfo("No Results", "No results found for the search term.")

        except Exception as e:
            messagebox.showerror("Search Error", f"Error during search: {str(e)}")

    def browse_address(self):
        """Browse specific address"""
        address = simpledialog.askstring(
            "Browse Address",
            "Enter hexagonal address (format: hex-w1-s1-v1:1):",
            parent=self.root
        )

        if not address:
            return

        self.show_processing("Generating page content...")

        try:
            content = self.library.generate_page_from_address(address)

            if "Invalid address format" in content:
                messagebox.showerror("Invalid Address", "The address format is invalid.")
                return

            result_text = f"Page Content for Address: {address}\n"
            result_text += "=" * 50 + "\n\n"
            result_text += content

            self.create_results_window(f"Page Content - {address}", result_text)

        except Exception as e:
            messagebox.showerror("Browse Error", f"Error browsing address: {str(e)}")

    def browse_hex_structure(self):
        """Browse hex structure"""
        hex_name = simpledialog.askstring(
            "Browse Hex Structure",
            "Enter hex name (or leave empty for random):",
            parent=self.root
        )

        if hex_name is None:
            return

        if not hex_name:
            hex_name = self.library._generate_hex_name(str(random.random()), 0)

        self.show_hex_browser(hex_name)

    def show_hex_browser(self, hex_name, wall=None, shelf=None, volume=None):
        """Display hex browser window"""
        browser_window = tk.Toplevel(self.root)
        browser_window.title(f"Hex Browser - {hex_name[:20]}...")
        browser_window.geometry("900x700")
        browser_window.configure(bg=self.bg_color)

        nav_text = f"Hex: {hex_name[:20]}..."
        if wall is not None:
            nav_text += f" → Wall {wall}"
        if shelf is not None:
            nav_text += f" → Shelf {shelf}"
        if volume is not None:
            nav_text += f" → Volume {volume}"

        nav_label = tk.Label(
            browser_window,
            text=nav_text,
            font=("Arial", 12, "bold"),
            bg=self.bg_color,
            fg=self.highlight_color
        )
        nav_label.pack(pady=10)

        try:
            items = self.library.browse_hex_structure(hex_name, wall, shelf, volume)

            list_frame = tk.Frame(browser_window, bg=self.bg_color)
            list_frame.pack(fill='both', expand=True, padx=20, pady=10)

            scrollbar = tk.Scrollbar(list_frame)
            scrollbar.pack(side='right', fill='y')

            listbox = tk.Listbox(
                list_frame,
                font=("Courier", 10),
                bg=self.button_bg,
                fg=self.fg_color,
                selectbackground=self.highlight_color,
                yscrollcommand=scrollbar.set
            )
            listbox.pack(side='left', fill='both', expand=True)
            scrollbar.config(command=listbox.yview)

            for item in items:
                display_text = f"{item['identifier']} - {item['preview'][:60]}..."
                listbox.insert('end', display_text)

            def on_select(event):
                selection = listbox.curselection()
                if selection:
                    item = items[selection[0]]
                    if item['type'] == 'wall':
                        self.show_hex_browser(hex_name, int(item['identifier'].split()[1]))
                    elif item['type'] == 'shelf':
                        self.show_hex_browser(hex_name, wall, int(item['identifier'].split()[1]))
                    elif item['type'] == 'volume':
                        self.show_hex_browser(hex_name, wall, shelf, int(item['identifier'].split()[1]))
                    elif item['type'] == 'page':
                        content = self.library.generate_page_from_address(item['address'])
                        self.create_results_window(f"Page - {item['address']}", content)

            listbox.bind('<Double-1>', on_select)

        except Exception as e:
            messagebox.showerror("Browser Error", f"Error browsing hex structure: {str(e)}")

    def random_page(self):
        """Generate random page"""
        self.show_processing("Generating random page...")

        try:
            page_data = self.library.generate_random_page()

            result_text = f"Random Page\n"
            result_text += "=" * 50 + "\n\n"
            result_text += f"Address: {page_data['address']}\n"
            result_text += f"Location: Wall {page_data['wall']}, Shelf {page_data['shelf']}, "
            result_text += f"Volume {page_data['volume']}, Page {page_data['page']}\n\n"
            result_text += "Content:\n"
            result_text += page_data['content']

            self.create_results_window("Random Page", result_text)

        except Exception as e:
            messagebox.showerror("Generation Error", f"Error generating random page: {str(e)}")

    def show_statistics(self):
        """Display library statistics"""
        stats_text = f"""Refined Library of Babel Statistics

Enhanced Search Features:
• Exact matches preserve full searched text
• Similar matches include text with end spaces
• Similar matches include text as substring
• Perfect bidirectional consistency maintained

Character Set: 29 characters (a-z, space, comma, period)
Page Length: 1000 characters
Hex Name Length: 120 characters
Library Structure: 1-based indexing

Current Seed: {self.library.CONSTANT_SEED}

The refined search ensures that:
1. EXACT matches contain the complete searched text
2. SIMILAR matches are either exact text with spaces OR exact text as substring
3. All results maintain perfect character-level accuracy"""

        messagebox.showinfo("Refined Search Statistics", stats_text)

    def show_processing(self, message):
        """Show processing dialog"""
        processing_window = tk.Toplevel(self.root)
        processing_window.title("Processing")
        processing_window.geometry("300x100")
        processing_window.configure(bg=self.bg_color)
        processing_window.resizable(False, False)

        processing_window.transient(self.root)
        processing_window.grab_set()

        label = tk.Label(
            processing_window,
            text=message,
            font=("Arial", 12),
            bg=self.bg_color,
            fg=self.fg_color
        )
        label.pack(expand=True)

        processing_window.update()
        self.root.after(500, processing_window.destroy)

    def run(self):
        """Start the application"""
        self.root.mainloop()


if __name__ == "__main__":
    app = LibraryOfBabelGUI()
    app.run()
