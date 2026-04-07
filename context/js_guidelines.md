# JavaScript / TypeScript / React — Coding Guidelines

These guidelines apply to all JavaScript, TypeScript, React, Astro, and Node.js
repositories in the organization. They are loaded into the AI reviewer's system
prompt when the detected profile is `react`, `astro`, or `node`.

---

## General JavaScript / TypeScript

### Code style
- Use `const` for values that are never reassigned; `let` for values that are.
  Never use `var`.
- Prefer arrow functions for callbacks and short utilities.
- Use template literals instead of string concatenation.
- Avoid implicit type coercions (`==` vs `===`). Always use strict equality (`===`).
- Destructure objects and arrays when extracting multiple values.
- Use optional chaining (`?.`) and nullish coalescing (`??`) instead of manual
  null checks where it improves readability.

### TypeScript
- Enable `strict` mode in `tsconfig.json`. New projects must not disable it.
- All public function signatures (parameters + return type) must be typed.
- Avoid `any`. If `any` is truly necessary, add an explanatory comment.
- Prefer `interface` for object shapes; use `type` for unions, intersections,
  and mapped types.
- Use `unknown` instead of `any` for values whose type is not yet known
  (e.g. API responses), then narrow with type guards.
- Never use `!` non-null assertion without a comment explaining why the value
  cannot be null at that point.

### Imports
- Use ES module syntax (`import`/`export`). No CommonJS (`require`) in TypeScript
  files unless interoperating with a CJS-only package.
- Group imports: stdlib / framework / third-party / internal. Separate with a
  blank line.
- Avoid barrel files (`index.ts` that re-exports everything) in large directories;
  they increase bundle size and slow down TypeScript compilation.

### Error handling
- Always handle promise rejections: use `try/catch` in `async` functions or
  `.catch()` on raw promises.
- Never swallow errors silently (`catch (_e) {}`). Log or rethrow.
- Use typed error handling where possible:
  ```ts
  if (error instanceof SomeError) { ... }
  ```

### Security
- Never use `eval()`, `new Function()`, or `setTimeout(code_string)`.
- Never insert untrusted strings into the DOM via `innerHTML` or
  `dangerouslySetInnerHTML` without sanitizing with a vetted library (e.g. DOMPurify).
- All API boundary inputs must be validated (use Zod, Valibot, or similar).
- No hardcoded secrets, tokens, or passwords. Use environment variables.
- All environment variables accessed at runtime must be documented in `.env.example`.

### Logging
- No `console.log`, `console.debug`, or `debugger` statements in production code.
  Use a structured logger (e.g. `pino`, custom logger utility).
- `console.warn` and `console.error` are acceptable for genuine warnings/errors
  but should eventually be replaced with a structured logger.

---

## React

### Components
- Prefer function components. Do not write class components for new code.
- One component per file. File name matches the component name (`PascalCase.tsx`).
- Props must have an explicit TypeScript interface or type alias defined in the
  same file (or in a co-located `*.types.ts` file).
- Avoid prop drilling beyond 2 levels — use context, Zustand, or similar.

### Hooks
- Follow the Rules of Hooks:
  - Only call hooks at the top level of a function component or custom hook.
  - Never call hooks inside loops, conditions, or nested functions.
- `useEffect` dependencies array must be complete. Omitting a dependency that
  is used inside the effect is a bug (stale closure).
- For effects that start subscriptions or async operations, always return a
  cleanup function.
  ```ts
  useEffect(() => {
    const controller = new AbortController();
    fetch(url, { signal: controller.signal }).then(...);
    return () => controller.abort();
  }, [url]);
  ```
- Use `useMemo` and `useCallback` only when there is a documented performance
  reason. Premature memoization adds noise.

### Keys
- The `key` prop on list items must be stable and unique within the list.
- Never use array index as `key` when items can be reordered, inserted, or
  deleted. Use a stable ID from the data.

### State management
- Keep state as close to where it is used as possible.
- Derive values from state instead of duplicating state.
  ```ts
  // GOOD
  const isDisabled = items.length === 0;
  // BAD
  const [isDisabled, setIsDisabled] = useState(false);  // duplicates state
  ```

### Performance
- Avoid creating new object literals, array literals, or function expressions
  inside JSX props/attributes — they break `React.memo` and `useMemo`.
  Move them outside the render or wrap in `useMemo`/`useCallback`.
- Use `React.memo` for components that render frequently with the same props.
- Use `React.lazy` + `Suspense` for code-splitting large sub-trees.

### Accessibility
- All interactive elements (`<button>`, `<a>`, `<input>`, etc.) must have
  accessible names (visible text, `aria-label`, or `aria-labelledby`).
- Do not use non-semantic elements (e.g. `<div>`) for interactive purposes
  without ARIA roles.
- Images must have `alt` attributes; decorative images use `alt=""`.
- Use `<button>` for actions, `<a>` for navigation. Do not mix them up.

---

## Astro

### Component structure
- The frontmatter script (`---`) block must be valid TypeScript/JavaScript.
- Server-only code (DB queries, API calls that use private keys) must stay in
  the frontmatter. Never expose server secrets to the client.
- Use `client:*` directives only when interactivity is genuinely needed.
  Prefer `client:idle` and `client:visible` over `client:load` to reduce TBT.

### Content collections
- All content collection schemas must be defined with Zod in `src/content/config.ts`.
- Frontmatter fields must match the schema exactly.

### Routing
- Dynamic routes using `[slug].astro` must export `getStaticPaths()` for SSG mode.
- Use `Astro.redirect()` for server-side redirects; never use meta-refresh or
  `window.location` for primary navigation.

### Images
- Use Astro's built-in `<Image>` component for local images to enable
  automatic optimization.
- Provide `width`, `height`, and `alt` on every `<Image>`.

---

## Node.js

### Process management
- Never call `process.exit()` in library code — only in the top-level CLI entry
  point or after cleanup.
- Handle `uncaughtException` and `unhandledRejection` at the process level to
  log and perform graceful shutdown. Do not use them to swallow errors.

### HTTP / API
- All routes must validate their inputs. Use a schema validation library.
- Set appropriate timeouts on outgoing HTTP requests.
- Never log request bodies that may contain sensitive data (passwords, tokens,
  PII). Sanitize before logging.

### Dependencies
- New runtime dependencies require a justification comment in the PR description.
- Avoid dependencies with no maintenance activity for >2 years, especially for
  security-sensitive functions (auth, crypto, parsing).
- Pin major versions in `package.json`. Do not use `*` or `latest`.

---

## Commit message format

Follow the organization-wide `[TAG] scope: description` format:

```
[ADD] auth: add JWT refresh-token endpoint
[FIX] cart: fix total calculation when discount is 0
[IMP] ui: improve mobile layout for checkout form
[REF] api: extract validation logic into shared helper
[REM] legacy: remove deprecated OAuth1 adapter
```

Tags: `[ADD]` `[FIX]` `[UPD]` `[REF]` `[REM]` `[MOV]` `[IMP]` `[REL]` `[MERGE]`
`[REV]` `[CLN]` `[LINT]` `[PERF]` `[I18N]` `[CLA]`
