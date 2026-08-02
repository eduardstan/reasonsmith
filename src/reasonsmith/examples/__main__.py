"""Print where the example systems and the sample decision log were installed.

`reasonsmith check --system` takes a filesystem path, and after `pip install reasonsmith` the
sample log is inside site-packages. This prints that directory so a documented command can name
the file without the reader hunting for it:

    reasonsmith check --system "$(python -m reasonsmith.examples)/sample_decisions.jsonl" \
        --pack ecoa --system-name CreditScoringPipeline --system-domain consumer-credit
"""

from reasonsmith.examples import EXAMPLES_DIR

print(EXAMPLES_DIR)
