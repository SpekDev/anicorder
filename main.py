import mariadb
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.theme import Theme
from textual.widgets import Button, DataTable, Footer, Input, Label, MaskedInput, Select
from titlecase import titlecase


def convert_seconds_to_column(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def convert_column_to_seconds(timecolumn):
    times = [3600, 60, 1]
    return sum([a * b for a, b in zip(times, map(int, timecolumn.split(":")))])


BEASTIE_THEME = Theme(
    name="beastie",
    primary="#AB2B28",
    secondary="#5E8AAA",
    accent="#AB2B28",
    foreground="#D4D4D4",
    background="#1C2028",
    surface="#262A32",
    panel="#161A20",
    boost="#CC3533",
    warning="#CC9933",
    error="#DD4444",
    success="#55AA66",
    dark=True,
)


# Screens
class Manage_Anime_Screen(Screen):
    def compose(self) -> ComposeResult:
        yield Button("<- Back", id="manage_anime_back_button", action="app.quit")
        yield Input(id="manage_anime_input", placeholder="Search for Entry")
        yield Button("Enter", id="manage_anime_enter", action="app.query")
        yield DataTable(
            id="manage_data_table",
            cursor_type="row",
            zebra_stripes=True,
            show_cursor=True,
        )

    def on_mount(self):
        data_table = self.query_one("#manage_data_table", DataTable)
        data_table.add_column("id")
        data_table.add_column("Title", width=70)
        data_table.add_column("Completion Status", width=20)
        data_table.disabled = True

    def on_screen_resume(self) -> None:
        data_table = self.query_one("#manage_data_table", DataTable)
        data_table.clear()
        self.app.manage_offset = 0
        self.app.action_query()

    def key_enter(self):
        focused = self.app.focused
        if isinstance(focused, DataTable):
            data_table = self.query_one("#manage_data_table", DataTable)
            row_key, _ = data_table.coordinate_to_cell_key(data_table.cursor_coordinate)
            row = data_table.get_row(row_key)
            id = row[0]
            anime = self.app.get_anime(id)
            self.app.push_screen(Interactive_Manage_Flyout(anime))
        elif isinstance(focused, Input):
            self.focus_next()


class Record_Anime_Screen(Screen):
    def compose(self) -> ComposeResult:
        yield Button("<- Back", id="record_anime_back_button", action="app.quit")
        yield Input(id="record_anime_input", placeholder="Enter English Title")
        yield Button(
            "Record Anime", id="record_anime_button", disabled=True, classes="invalid"
        )

    def on_input_submitted(self):
        normal_input = titlecase(
            self.screen.query_one("#record_anime_input", Input).value
        ).strip()
        if self.app.record_check_anime(normal_input) is None:
            sql = r"INSERT INTO anime (english_title, status) VALUES (?, ?)"
            data = (normal_input, "watching")
            self.app.insert_into_db(sql, data)
            self.app.action_quit()
            self.notify("Entry Added", title="Database Message", severity="information")
        else:
            self.notify(
                "Entry already exists ", title="Database Message", severity="error"
            )
            self.app.action_quit()


class Connect_DB_Screen(Screen):
    def compose(self) -> ComposeResult:
        yield Button("<- Back", id="connect_db_back_button", action="app.quit")
        yield Input(
            value="localhost",
            valid_empty=False,
            id="db_server",
            placeholder="IP Address",
        )
        yield Input(
            value="anicorder",
            valid_empty=False,
            id="db_db",
            placeholder="Database Name",
        )
        yield Input(
            value="anime",
            valid_empty=False,
            id="db_table",
            placeholder="Database Table",
        )
        yield Input(
            value="root",
            valid_empty=False,
            id="db_username",
            placeholder="Database Username",
        )  # Ensure user has read and append permissions
        yield Input(
            id="db_pass",
            password=True,
            select_on_focus=True,
            placeholder="Database Password",
        )
        yield Button("Connect to DB", id="connect_button", action="app.connect_db")


class Interactive_Manage_Flyout(ModalScreen):
    BINDINGS = [
        Binding("q, ctrl+q, escape", "app.quit", "Quit"),  # Pops the screen
        Binding(
            "h, left, a", "app.go_left", "Move left or back", show=False
        ),  # Vim style binds
        Binding("l, right, d ", "app.go_right", "Move right", show=False),
        Binding("w, up, k", "app.go_up", "Move up", show=False),
        Binding("s, down, j", "app.go_down", "Move down", show=False),
    ]

    changed = reactive(False)

    def __init__(self, anime):
        super().__init__()
        (
            self.anime_id,
            self.english_title,
            self.status,
            self.episode,
            self.time_in_seconds,
        ) = anime

    def compose(self) -> ComposeResult:
        with Container():
            yield Label(f"{self.english_title}", id="modal_title")
            with Horizontal(id="episode_timestamp_container"):
                with Horizontal():
                    yield Label(f"Episode: ")
                    yield MaskedInput(
                        template="9999", id="episode_entry", value=str(self.episode)
                    )
                with Horizontal():
                    yield Label("Timestamp: ")
                    yield MaskedInput(
                        template="99:99:99",
                        id="time_column_entry",
                        value=convert_seconds_to_column(self.time_in_seconds),
                    )
            with Horizontal(id="status_container"):
                yield Label("Status: ")
                yield Select(
                    [
                        ("To Be Animated", "tba"),
                        ("To Be Watched", "tbw"),
                        ("Watching", "watching"),
                        ("Completed", "completed"),
                        ("Dropped/Abandoned", "dropped"),
                    ],
                    id="status_select",
                    type_to_search=False,
                    value=self.status,
                    compact=True,
                    allow_blank=False,
                )

            yield Button(
                "Remove Entry",
                id="remove_entry_details",
                action=f"app.remove_entry({self.anime_id})",
            )
            yield Button(
                "Modify Entry",
                id="modify_entry_details",
                action=f"app.modify_entry({self.anime_id})",
                disabled=True,
            )

    def on_input_changed(self) -> None:
        self.changed = True

    def on_select_changed(self) -> None:
        self.changed = True

    def watch_changed(self, changed: bool):
        self.query_one("#modify_entry_details", Button).disabled = not changed


class Anicorder(App):
    CSS_PATH = "style.tcss"

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding(
            "q, ctrl+q, escape", "quit", "Quit"
        ),  # Pops the screen, override to quit the app if it is the last screen on stack
        Binding("r", "toggle_theme", "Toggle Theme"),
        Binding(
            "h, left, a", "go_left", "Move left or back", show=False
        ),  # Vim style binds
        Binding("l, right, d ", "go_right", "Move right", show=False),
        Binding("w, up, k", "go_up", "Move up", show=False),
        Binding("s, down, j", "go_down", "Move down", show=False),
    ]

    SCREENS = {
        "manage_anime": Manage_Anime_Screen,
        "record_anime": Record_Anime_Screen,
        "connect_db": Connect_DB_Screen,
    }

    def compose(self) -> ComposeResult:

        yield Label(
            r"""
            ______             __                                      __
           /      \           |  \                                    |  \
          |  $$$$$$\ _______   \$$  _______   ______    ______    ____| $$  ______    ______
          | $$__| $$|       \ |  \ /       \ /      \  /      \  /      $$ /      \  /      \
          | $$    $$| $$$$$$$\| $$|  $$$$$$$|  $$$$$$\|  $$$$$$\|  $$$$$$$|  $$$$$$\|  $$$$$$\
          | $$$$$$$$| $$  | $$| $$| $$      | $$  | $$| $$   \$$| $$  | $$| $$    $$| $$   \$$
          | $$  | $$| $$  | $$| $$| $$_____ | $$__/ $$| $$      | $$__| $$| $$$$$$$$| $$
          | $$  | $$| $$  | $$| $$ \$$     \ \$$    $$| $$       \$$    $$ \$$     \| $$
           \$$   \$$ \$$   \$$ \$$  \$$$$$$$  \$$$$$$  \$$        \$$$$$$$  \$$$$$$$ \$$



            """,
            id="ascii_title",
            classes="home",
            markup=False,
        )

        yield Button(
            "Manage Anime",
            id="home_manage",
            variant="default",
            classes="home",
            disabled=True,
        )
        yield Button(
            "Record Anime",
            id="home_record",
            variant="default",
            classes="home",
            disabled=True,
        )
        yield Button("Connect To DB", id="home_db", variant="default", classes="home")
        yield Button("Quit", id="home_quit", variant="default", classes="home")

        with Horizontal():
            yield Label("Completed Animes: 0", id="completed-count")
            yield Label("Total Animes: 0", id="total-count")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(BEASTIE_THEME)
        self.theme = "beastie"
        self.conn = None
        self.manage_offset = 0
        self.completed_anime_count_label = self.query_one("#completed-count", Label)
        self.total_anime_count_label = self.query_one("#total-count", Label)
        self.prev_specific_search = False

    def action_connect_db(self):
        if self.conn is None:
            try:
                server = self.screen.query_one("#db_server", Input).value
                db = self.screen.query_one("#db_db", Input).value
                table = self.screen.query_one("#db_table", Input).value
                user = self.screen.query_one("#db_username", Input).value
                password = self.screen.query_one("#db_pass", Input).value

                self.conn = mariadb.connect(
                    host=server,
                    database=db,
                    user=user,
                    password=password,
                    connect_timeout=7,
                    ssl=True,
                )
                self.notify(
                    f"Connection to Database established",
                    title="Connection Status",
                    severity="information",
                    timeout=5,
                )
                self.screen.query_one("#connect_button", Button).disabled = True

                with self.conn.cursor() as cursor:
                    cursor.execute(
                        r"SELECT COUNT(*) FROM anime WHERE status='completed'"
                    )
                    completed_count = cursor.fetchone()[0]
                    cursor.execute(r"SELECT COUNT(*) FROM anime")
                    total_count = cursor.fetchone()[0]

                self.pop_screen()
                self.screen.query_one("#home_manage", Button).disabled = False
                self.screen.query_one("#home_record", Button).disabled = False
                self.completed_anime_count_label.update(
                    f"Completed Animes: {completed_count}"
                )
                self.total_anime_count_label.update(f"Total Animes: {total_count}")
            except mariadb.Error as e:
                self.conn = None
                self.notify(
                    f"Connection to Database Failed!\nError: {e}",
                    title="Connection Status",
                    severity="error",
                    timeout=7,
                )

        return self.conn

    def get_db(self):
        return self.action_connect_db()

    def close_db(self):
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None

    def insert_into_db(self, sql, data):
        with self.conn.cursor() as cur:
            cur.execute(sql, data)
        self.conn.commit()

    def action_query(self) -> None:
        chunk_size = 10
        data_table = self.screen.query_one("#manage_data_table", DataTable)
        data_table.disabled = False
        manage_cursor = self.conn.cursor()
        if (
            input_text := self.screen.query_one(
                "#manage_anime_input", Input
            ).value.strip()
        ) == "":
            if self.prev_specific_search:
                data_table.clear()
            self.prev_specific_search = False
            sql = r"SELECT id, english_title, status FROM anime ORDER BY id LIMIT ? OFFSET ?"
            data = (chunk_size, self.manage_offset)
            self.manage_offset += chunk_size
        else:
            data_table.clear()
            self.manage_offset = 0
            sql = r"SELECT id, english_title, status FROM anime WHERE english_title LIKE ? ORDER BY english_title"
            data = (f"{titlecase(input_text)}%",)
            self.prev_specific_search = True

        manage_cursor.execute(sql, data)
        for i in manage_cursor.fetchall():
            data_table.add_row(*i, key=i[0])

    def get_anime(self, anime_id):
        with self.conn.cursor() as cur:
            cur.execute(r"SELECT * FROM anime WHERE id = ?", (anime_id,))
            return cur.fetchone()

    def refresh_anime_count(self):

        with self.conn.cursor() as cursor:
            cursor.execute(r"SELECT COUNT(*) FROM anime WHERE status='completed'")
            completed_count = cursor.fetchone()[0]
            cursor.execute(r"SELECT COUNT(*) FROM anime")
            total_count = cursor.fetchone()[0]

        self.completed_anime_count_label.update(f"Completed Animes: {completed_count}")
        self.total_anime_count_label.update(f"Total Animes: {total_count}")

    def record_check_anime(self, title):
        with self.conn.cursor() as cur:
            cur.execute(
                r"SELECT english_title FROM anime WHERE english_title=?", (title,)
            )
            return cur.fetchone()

    def action_modify_entry(self, anime_id):
        new_status = self.screen.query_one("#status_select", Select).selection
        try:
            new_episode = self.screen.query_one("#episode_entry", MaskedInput).value
        except ValueError:
            self.notify(
                "Please enter a epidsode value", title="Data Error", severity="error"
            )
        try:
            new_time = convert_column_to_seconds(
                self.screen.query_one("#time_column_entry", MaskedInput).value
            )
        except ValueError:
            self.notify(
                "Please enter a time value", title="Data Error", severity="error"
            )
            return

        with self.conn.cursor() as cur:
            sql = r"UPDATE anime SET status=?, episode=?, time_watched_in_seconds=? WHERE id=?"
            data = (new_status, new_episode, new_time, anime_id)
            cur.execute(sql, data)
            self.conn.commit()
        self.app.action_quit()
        self.notify(
            f"Entry Updated!",
            title="Database Message",
            severity="information",
            timeout=3,
        )

    def action_remove_entry(self, anime_id):
        with self.conn.cursor() as cur:
            sql = r"DELETE FROM anime WHERE id=?"
            data = (anime_id,)
            cur.execute(sql, data)
            self.conn.commit()
        self.app.action_quit()
        self.notify(
            f"Entry Removed!", title="Database Message", severity="warning", timeout=3
        )

    def action_toggle_theme(self) -> None:
        self.theme = "beastie" if self.theme == "solarized-light" else "solarized-light"

    def action_go_down(self) -> None:
        self.action_focus_next()

    def action_go_up(self) -> None:
        self.action_focus_previous()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "home_manage":
                self.push_screen("manage_anime")
            case "home_record":
                self.push_screen("record_anime")
            case "home_db":
                self.push_screen("connect_db")
            case "home_quit":
                self.exit()

    def action_quit(self) -> None:
        if len(self.screen_stack) > 1:
            if self.conn != None:
                self.refresh_anime_count()
            self.pop_screen()
        else:
            self.close_db()
            self.exit()

    def on_shutdown(self) -> None:
        self.close_db()


if __name__ == "__main__":
    Anicorder().run()
