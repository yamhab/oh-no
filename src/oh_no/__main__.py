"""UNO in the terminal."""

import contextlib
import dataclasses
import enum
import random

import blessed
import wcwidth

_MIN_WIDTH = 80
_MIN_HEIGHT = 24

_START_LOGO = """  ___   __        ____  _____         _
 .'   `.[  |      |_   \\|_   _|       | |
/  .-.  \\| |--.     |   \\ | |   .--.  | |
| |   | || .-. |    | |\\ \\| | / .'`\\ \\| |
\\  `-'  /| | | |   _| |_\\   |_| \\__. ||_|
 `.___.'[___]|__] |_____|\\____|'.__.' (_)"""

_MIN_PLAYERS = 2
_MAX_PLAYERS = 8

_HAND_CARDS = 7


class _Color(enum.IntEnum):
    """A card's color."""

    RED = enum.auto()
    YELLOW = enum.auto()
    GREEN = enum.auto()
    BLUE = enum.auto()
    WILD = enum.auto()

    def render(self, term: blessed.Terminal) -> str:
        """Return the colored string to be printed to the terminal of the card's color."""
        rendered = ""
        match self:
            case self.RED:
                rendered = term.red_reverse + "RED"
            case self.YELLOW:
                rendered = term.yellow_reverse + "YELLOW"
            case self.GREEN:
                rendered = term.green_reverse + "GREEN"
            case self.BLUE:
                rendered = term.blue_reverse + "BLUE"
            case self.WILD:
                rendered = term.magenta_reverse + "WILD"
        return rendered


class _Type(enum.IntEnum):
    """A card's type."""

    NUMBER = enum.auto()
    SKIP = enum.auto()
    REVERSE = enum.auto()
    DRAW_TWO = enum.auto()
    WILD = enum.auto()
    WILD_DRAW_FOUR = enum.auto()

    def render(self) -> str:
        """Return the colored string to be printed to the terminal of the card's type."""
        rendered = ""
        match self:
            case self.SKIP:
                return "SKIP"
            case self.REVERSE:
                return "REVERSE"
            case self.DRAW_TWO:
                return "DRAW TWO"
            case self.WILD_DRAW_FOUR:
                return "DRAW FOUR"
        return rendered


@dataclasses.dataclass(order=True)
class _Card:
    """An Oh No card."""

    color: _Color
    type: _Type
    number: int | None = None

    def render(self, term: blessed.Terminal) -> str:
        """Return the colored string to be printed to the terminal of the card."""
        if self.type == _Type.NUMBER:
            return self.color.render(term) + " " + str(self.number) + term.normal
        if self.type == _Type.WILD:
            return self.color.render(term) + term.normal
        return self.color.render(term) + " " + self.type.render() + term.normal

    def playable(self, last: _Card) -> bool:
        """Return whether its possible to play a card after another."""
        return (
            self.type in {_Type.WILD, _Type.WILD_DRAW_FOUR}
            or self.type == last.type != _Type.NUMBER
            or self.color == last.color
            or self.number == last.number is not None
        )


@dataclasses.dataclass
class Game:
    """All the game's state."""

    term: blessed.Terminal
    _num: int = 0
    _current: int = 0
    _direction: int = 1
    _deck: list[_Card] = dataclasses.field(default_factory=list)
    _hands: list[list[_Card]] = dataclasses.field(default_factory=list)
    _stack: list[_Card] = dataclasses.field(default_factory=list)
    _skip: bool = False
    _draw: int = 0

    def play(self) -> None:
        """Run the game's main loop."""
        if self.term.width < _MIN_WIDTH or self.term.height < _MIN_HEIGHT:
            print(
                f"Minimum terminal dimensions: {_MIN_WIDTH}x{_MIN_HEIGHT}\nCurrent terminal \
dimensions: {self.term.width}x{self.term.height}",
            )
            return

        with self.term.fullscreen():
            self._setup_players()
            self._setup_cards()

            for _ in range(self._num):
                print(self.term.clear() + self.term.center("~~~ PLAYER 1's TURN ~~~"))
                self._print_hand()
                self._choose_card()
                self._card_action()
                with self.term.cbreak(), self.term.hidden_cursor():
                    print("Press any key to continue... ")
                    self.term.inkey()

                while len(self._hands[self._current]) != 0:
                    self._turn()
                    with self.term.cbreak(), self.term.hidden_cursor():
                        print("Press any key to continue... ")
                        self.term.inkey()

                print(f"{self.term.clear()}Player {self._current + 1} wins!")

    def _setup_players(self) -> None:
        """Greet the player and get the number of players."""
        print(self.term.clear() + "\n")
        for line in _START_LOGO.splitlines():
            print(self.term.center(line))
        print("\n" + self.term.center("Press CTRL-C to exit at any time"))
        print(self.term.center("Welcome to Oh No! How many people will be playing (2-8)?"))

        while self._num < _MIN_PLAYERS or self._num > _MAX_PLAYERS:
            with contextlib.suppress(ValueError):
                self._num = int(self._center_input("> "))
            print(
                self.term.move_x(0) + self.term.move_up() + self.term.clear_eol(),
                end="",
            )

    def _center_input(self, prompt: str) -> str:
        """Read a string from standard input with a centered prompt."""
        if prompt.isascii() and prompt.isprintable():
            text_width = len(prompt)
        else:
            text_width = wcwidth.width(prompt, control_codes="ignore")
        total_padding = max(0, self.term.width - text_width)
        left_pad = total_padding // 2 + (total_padding & self.term.width & 1) - 1
        return input(" " * left_pad + prompt)

    def _setup_cards(self) -> None:
        """Shuffle a deck and deal an appropriate number of cards to each player."""
        for color in [_Color.RED, _Color.YELLOW, _Color.GREEN, _Color.BLUE]:
            self._deck.append(_Card(color, _Type.NUMBER, 0))
            for number in range(1, 10):
                self._deck.extend(_Card(color, _Type.NUMBER, number) for _ in range(2))
            self._deck.extend(_Card(color, _Type.SKIP) for _ in range(2))
            self._deck.extend(_Card(color, _Type.REVERSE) for _ in range(2))
            self._deck.extend(_Card(color, _Type.DRAW_TWO) for _ in range(2))
        self._deck.extend(_Card(_Color.WILD, _Type.WILD) for _ in range(4))
        self._deck.extend(_Card(_Color.WILD, _Type.WILD_DRAW_FOUR) for _ in range(4))
        random.shuffle(self._deck)

        for hand in range(self._num):
            self._hands.append(self._deck[-_HAND_CARDS:])
            del self._deck[-_HAND_CARDS:]
            self._hands[hand].sort()

    def _print_hand(self, playable: list[int] | None = None) -> None:
        """Print the current player's hand and list cards playable on the stack's last card."""
        print("Here are the cards in your hand:")
        for i, card in enumerate(self._hands[self._current]):
            print(f"{i + 1}: {card.render(self.term)}")
        if len(self._stack) != 0:
            print(f"The last played card on the stack was a {self._stack[-1].render(self.term)}.")
        if playable:
            print("You may play one of the following cards from your hand:")
            for i, card in enumerate(playable):
                if i < len(playable) - 1:
                    print(card + 1, end=", ")
                else:
                    print(card + 1)

    def _choose_card(self, playable: list[int] | None = None) -> None:
        """Ask the current player for what card from their hand to play, and play it if possible."""
        while True:
            with contextlib.suppress(ValueError, IndexError):
                choice = int(input("Which card would you like to play? ")) - 1
                if not playable or choice in playable:
                    self._play_card(choice)
                    if len(self._hands[self._current]) == 1:
                        print("Oh No!")
                    break
            print(
                self.term.move_x(0) + self.term.move_up() + self.term.clear_eol(),
                end="",
            )

    def _play_card(self, choice: int) -> None:
        """Play the card indexed from the current player's hand."""
        self._stack.append(self._hands[self._current][choice])
        print("You play a " + self._hands[self._current][choice].render(self.term))
        del self._hands[self._current][choice]

    def _card_action(self) -> None:
        """Perform the stack's last played card's action (based off of its type), if needed."""
        last = self._stack[-1]
        match last.type:
            case _Type.SKIP:
                self._skip = True
            case _Type.REVERSE:
                self._direction *= -1
            case _Type.DRAW_TWO:
                self._skip = True
                self._draw = 2
            case _Type.WILD:
                self._choose_color()
            case _Type.WILD_DRAW_FOUR:
                self._choose_color()
                self._skip = True
                self._draw = 4

    def _choose_color(self) -> None:
        """Ask the current player for what color they'd like to switch their wild card to."""
        while True:
            match input("Which color would you like to switch to (R, Y, G, B)? ").lower():
                case "r":
                    self._stack[-1].color = _Color.RED
                    break
                case "y":
                    self._stack[-1].color = _Color.YELLOW
                    break
                case "g":
                    self._stack[-1].color = _Color.GREEN
                    break
                case "b":
                    self._stack[-1].color = _Color.BLUE
                    break
                case _:
                    print(
                        self.term.move_x(0) + self.term.move_up() + self.term.clear_eol(),
                        end="",
                    )

    def _turn(self) -> None:
        """Go through the current player's turn."""
        self._rotate()
        print(self.term.clear() + self.term.center(f"~~~ PLAYER {self._current + 1}'s TURN ~~~"))

        for _ in range(self._draw):
            self._draw_card()
        self._draw = 0

        if self._skip:
            self._print_hand()
            print("Turn skipped")
            self._skip = False
            return

        playable = self._playable_cards()
        card_played = False
        if len(playable) == 0:
            print("You have no valid cards to play")
            self._draw_card()
            playable = self._playable_cards()
            if len(playable) == 1:
                self._print_hand(playable)
                self._choose_card(playable)
                card_played = True
            else:
                self._print_hand()
        else:
            self._print_hand(playable)
            self._choose_card(playable)
            card_played = True

        if card_played:
            self._card_action()

    def _rotate(self) -> None:
        """Switch to the next player based off of the direction and number of players."""
        self._current += self._direction
        if self._current < 0:
            self._current += self._num
        else:
            self._current %= self._num

    def _draw_card(self) -> None:
        """Shuffle the stack into the deck if needed, and draw a card for the current player."""
        if len(self._deck) == 0:
            self._deck = self._stack.copy()
            self._stack.clear()
            self._deck.sort()

        card = self._deck.pop()
        print(f"You draw a {card.render(self.term)} from the deck")
        self._hands[self._current].append(card)
        self._hands[self._current].sort()

    def _playable_cards(self) -> list[int]:
        """Return a list of indices to all the playable cards from the current player's hand."""
        playable = []
        for i, card in enumerate(self._hands[self._current]):
            if card.playable(self._stack[-1]):
                playable.append(i)
        return playable


def main() -> None:
    """Entry point of the game."""
    term = blessed.Terminal()
    game = Game(term)
    game.play()


if __name__ == "__main__":
    main()
