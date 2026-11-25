# Diagram

The diagram is a single HTML page showing the system at the highest useful
altitude, with the unknowns drawn onto it. A box is coloured when a question,
a constraint or a fork attaches to it. Hovering a box shows the detail;
hovering a question lights up every box it touches.

The agent writes a JSON data file. `scripts/render_map.py` validates it and
fills `templates/design-map.html`. Never hand-edit the HTML.
`templates/design-map.example.json` is a complete worked example; read it
before writing a new one.

## What goes on it

It is a map of open decisions laid over a plausible shape of the system. It is
not the answer. Draw the boxes any sensible design would have, then mark where
the design is still undecided.

- 25 to 40 boxes. Fewer than 20 is usually missing the back office; more than
  40 is no longer a 10,000-foot view.
- One box per responsibility, named in plain words. No product or vendor names.
- Include the people. Personas are the top row, internal staff included.
- Include the outside parties the system depends on as the bottom row.
- Include the control plane and back office. Group them with a `groups` entry.

## Box kinds

| Kind | Use when | Must carry |
|---|---|---|
| `fork` | The design splits depending on an answer | `fork.q` and two or more `fork.options`, each with `name` and `when` |
| `constraint` | Something outside the team's control dictates behaviour here | `note` saying what imposes it |
| `open` | The box exists either way but its shape depends on unanswered questions | at least one entry in `qs` |
| `plain` | Needed either way and not in question | nothing extra |

A box takes the strongest kind that applies, in the order above. If more than
about a third of the boxes are forks, some of them are open questions. Add the
`plg` tag to any box the growth loop runs through.

Every option's `when` completes the sentence "Tips this way when ...". It
states a signal. It does not recommend.

## Data file

```json
{
  "title": "Venmo: design map at 10,000 ft",
  "prompt": "build me venmo",
  "columns": 6,
  "rows": ["People", "Entry", "Product services", "Money core", "Outside parties"],
  "groups": [{"label": "Back office", "col": 6, "fromRow": 2, "toRow": 4}],
  "categories": [{"key": "S", "name": "Scope", "blurb": "What the product is and is not"}],
  "questions": {"S1": {"q": "Is this person-to-person only?", "decides": "Whether seller flows exist."}},
  "first": ["S1"],
  "nodes": [
    {"id": "sender", "row": 1, "label": "Sender", "sub": "pays a friend", "kind": "open",
     "what": "Someone paying another person.", "expects": "It feels instant.", "qs": ["S1"]},
    {"id": "wallet", "row": 4, "col": 1, "label": "Wallet", "kind": "fork", "what": "What a user can spend.",
     "fork": {"q": "Do users hold a balance?", "options": [
       {"name": "Stored balance", "when": "receivers should be able to re-spend at once"},
       {"name": "Pass-through", "when": "holding customer money is to be avoided"}]},
     "qs": ["S1"]}
  ],
  "edges": [{"from": "sender", "to": "wallet", "route": "elbow"}]
}
```

- A question ID is its category key followed by a number. Questions are listed
  in the page in the order they appear in `questions`, so write them most
  important first within each category.
- `first` is the handful to ask if only a few can be asked.
- `expects` is for persona boxes: what that person needs from the system.
- `sub` is one short line under the label. Use it to state the open point
  ("in scope?", "stored balance, or pass-through?").

## Layout

The canvas is a grid of `rows` by `columns`.

- A row where no box has a `col` is a **strip**: its boxes share the full width
  evenly. Use strips for people and, if they do not need to line up with
  anything, outside parties.
- In every other row each box has a `col` and an optional `span`. A row is
  either all strip or all placed.
- Order rows the way a request travels: people, entry, product services, the
  core, events, async workers, outside parties.
- Put the back office in the last column and group it.

Edges only run through the gutters between rows and columns, never across a
box. Each edge names its route:

| Route | Draws | Allowed when |
|---|---|---|
| `elbow` | Down from the source, across the gutter, down into the target | Target is in the next row |
| `drop` | Straight down into the target from a wide source above it | Target is in the next row and under the source's columns |
| `down` | Straight down from the source | Source sits inside the target's columns and every cell between them is empty |
| `h` | Horizontal between neighbours | Same row, nothing between them |
| `margin` | Out of the left side, down the left margin, into the target | Source is in column 1, target is lower |
| `riser` | Down to the gutter, across to the gap beside the `via` box, down that gap, into the target | Target is lower; `via` names a box whose right-hand gap is clear all the way down (`"side": "left"` uses its left-hand gap) |

To keep lines from crossing:

- Place a box directly above what it feeds in the next row whenever possible.
- When a box must reach two or more rows down, leave the cells below it empty
  and use `down`, or send it along one `riser` gap and keep that gap free of
  horizontal edges.
- A wide box (an event stream spanning several columns) should feed its
  consumers with `drop` edges from the row above them.
- Two edges may share a gutter segment. They should not cross a vertical edge.
- Not every relationship needs a line. Leave out the ones the hover text
  explains.

## Rendering

```bash
python3 <path-to-this-skill>/scripts/render_map.py --data <map.json> --check
python3 <path-to-this-skill>/scripts/render_map.py --data <map.json> --output <map.html>
```

The script prints one JSON object. On `"ok": false`, fix every entry in
`errors` and run it again. `warnings` list boxes with no edges, questions
attached to no box, and open boxes with no questions; resolve them or be able
to say why each is fine.

Then open the page and look at it. Validation proves the lines avoid boxes. It
cannot prove the picture reads well. If the host has a browser, check that no
labels are clipped and that hovering a box shows its card. Tell the user the
full path of the file, and open it in their browser if the host can.
