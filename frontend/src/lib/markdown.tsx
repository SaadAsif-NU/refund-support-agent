import { Fragment, type ReactNode } from "react";

/*
 * Tiny markdown renderer matching the original: **bold** and newlines -> <br>.
 * React escapes text nodes automatically, so (unlike the innerHTML version)
 * there is no need to hand-escape &, <, > — it is safe by construction.
 */
export function renderMarkdown(text: string): ReactNode {
  return text.split("\n").map((line, lineIndex) => (
    <Fragment key={lineIndex}>
      {lineIndex > 0 && <br />}
      {renderBold(line)}
    </Fragment>
  ));
}

function renderBold(line: string): ReactNode {
  return line.split(/\*\*(.+?)\*\*/g).map((part, index) =>
    index % 2 === 1 ? (
      <strong key={index} className="font-bold text-white">
        {part}
      </strong>
    ) : (
      part
    ),
  );
}
