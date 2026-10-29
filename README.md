# Datapoort openEHR building blocks workshop

A paper building-block openEHR template-modelling workshop: participants build the *Nursing
Admission Assessment* template from printed archetype plates and building blocks, then author
a new archetype (*Inpatient admission details*) with write-on blocks. Adapted from the
EHRCON26 freshEHR/Hanze practical. No computers or internet needed on the day.

![The finished template: the Nursing Admission Assessment built up from the green Encounter baseplate](handouts/out/worked_example.png)

Try the online demo: <https://sophiedkk.github.io/datapoort-workshop/> (works on a laptop or a phone).

| Folder | What's in it |
|---|---|
| `handouts/` | The generator, and the print-ready files in `handouts/out/` |
| `archetypes/` | The archetypes and templates (Archetype Designer export) and the decoys |
| `forms/` | Word sources of the two paper forms |

## Running the workshop

The print-ready files are in the repository:

- [Participant handouts](handouts/out/participant_handouts.pdf)
- [Facilitator handouts](handouts/out/facilitator_handouts.pdf)
- [CKM desk](handouts/out/ckm_desk.pdf)
- [Baseplates (A0)](handouts/out/baseplates_A0.pdf)

Start with the first page of the facilitator handouts: it says what to print and how often, and
when to hand out what. Keep that page to yourself, it lists the decoys. The assignment takes the
participants through the exercises. Also bring scissors, pens and label paper for the stickers.

## Changing the materials

Rebuild everything with Podman:

```sh
podman build -t datapoort-handouts .
podman run --rm --userns=keep-id -v "$PWD:/work:Z" datapoort-handouts
```

Commit the files in `handouts/out/` afterwards; pushing `demo.html` to `main` updates the online
demo. See [handouts/README.md](handouts/README.md) for building without a container, the
generator scripts, the demo page and changing a paper form.
