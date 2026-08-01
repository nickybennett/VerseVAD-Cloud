"""Stable top-level navigation routes for the VerseVAD application shell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import streamlit as st


@dataclass(frozen=True)
class WorkspaceRoute:
    """One user-facing route and its shared workspace implementation."""

    section: str
    title: str
    workspace_id: str
    url_path: str
    icon: str
    default: bool = False
    local_only: bool = False


ROUTES: tuple[WorkspaceRoute, ...] = (
    WorkspaceRoute(
        "Analyze",
        "Single Poem",
        "Single Poem",
        "analyze-single-poem",
        ":material/description:",
        default=True,
    ),
    WorkspaceRoute(
        "Analyze",
        "Compare Poems",
        "Compare Poems",
        "analyze-compare-poems",
        ":material/compare_arrows:",
    ),
    WorkspaceRoute(
        "Analyze",
        "Other Text",
        "Other Text",
        "analyze-other-text",
        ":material/article:",
    ),
    WorkspaceRoute(
        "Analyze",
        "Lexicon Explorer",
        "Lexicon Explorer",
        "analyze-lexicon-explorer",
        ":material/search:",
    ),
    WorkspaceRoute(
        "Collections",
        "Personal Corpus",
        "Personal Corpus",
        "collections-personal-corpus",
        ":material/library_books:",
        local_only=True,
    ),
    WorkspaceRoute(
        "Collections",
        "Saved Projects",
        "Saved Projects",
        "collections-saved-projects",
        ":material/folder_open:",
    ),
    WorkspaceRoute(
        "Collections",
        "Reference Corpora",
        "Reference Corpora",
        "collections-reference-corpora",
        ":material/source:",
    ),
    WorkspaceRoute(
        "Collections",
        "Analysis Library",
        "Analysis Library",
        "collections-analysis-library",
        ":material/bookmarks:",
    ),
    WorkspaceRoute(
        "Explore",
        "VerseMap",
        "VerseMap",
        "explore-versemap",
        ":material/scatter_plot:",
    ),
    WorkspaceRoute(
        "Explore",
        "Lexicon Explorer",
        "Lexicon Explorer",
        "explore-lexicon-explorer",
        ":material/search:",
    ),
    WorkspaceRoute(
        "Explore",
        "Form Library",
        "Form Library",
        "explore-form-library",
        ":material/menu_book:",
    ),
    WorkspaceRoute(
        "Explore",
        "Corpus Browser",
        "Corpus Browser",
        "explore-corpus-browser",
        ":material/table_view:",
    ),
    WorkspaceRoute(
        "Learn",
        "Documentation",
        "Documentation",
        "learn-documentation",
        ":material/help_center:",
    ),
    WorkspaceRoute(
        "Learn",
        "Methodology",
        "Methodology",
        "learn-methodology",
        ":material/science:",
    ),
    WorkspaceRoute(
        "Learn",
        "Training",
        "Training",
        "learn-training",
        ":material/school:",
    ),
)

ROUTE_BY_PATH: Mapping[str, WorkspaceRoute] = {
    route.url_path: route for route in ROUTES
}
WORKSPACES: tuple[str, ...] = tuple(
    dict.fromkeys(route.workspace_id for route in ROUTES)
)


def _empty_page() -> None:
    """Leave page rendering to the shared monolithic workspace router."""


def _top_navigation_hover_html() -> str:
    """Return a progressive enhancement for desktop hover navigation.

    Streamlit's top navigation is click-first.  VerseVAD additionally opens a
    section after a short hover, then closes it once the pointer has left both
    the section trigger and its menu.  The delayed close keeps the small gap
    between those two elements traversable without making menus linger over
    the report beneath them.
    """

    return """
    <span
      data-versevad-topnav-hover
      aria-hidden="true"
      style="display:block;height:0;width:0;overflow:hidden;opacity:0"
    >.</span>
    <script>
      (() => {
        const OPEN_DELAY_MS = 160;
        const CLOSE_DELAY_MS = 220;
        let closeTimer = null;

        const cancelClose = () => {
          if (closeTimer !== null) window.clearTimeout(closeTimer);
          closeTimer = null;
        };

        const activeMenus = () =>
          Array.from(
            document.querySelectorAll(
              '[data-testid="stTopNavPopoverBody"]'
            )
          );

        const activeButtons = () =>
          Array.from(
            document.querySelectorAll(
              '[data-testid="stTopNavSection"][aria-expanded="true"]'
            )
          );

        const closeExpandedExcept = (buttonToKeep = null) => {
          activeButtons().forEach((button) => {
            if (button !== buttonToKeep) button.click();
          });
        };

        const pointerIsInsideNavigation = () => {
          return Boolean(
            document.querySelector(
              '[data-testid="stTopNavSection"]:hover'
            ) ||
            activeMenus().some((menu) => menu.matches(":hover"))
          );
        };

        const scheduleClose = () => {
          cancelClose();
          closeTimer = window.setTimeout(() => {
            closeTimer = null;
            if (pointerIsInsideNavigation()) return;
            closeExpandedExcept();
          }, CLOSE_DELAY_MS);
        };

        const bindMenuLeave = () => {
          activeMenus().forEach((menu) => {
            if (menu.dataset.versevadHoverBound === "true") return;
            menu.dataset.versevadHoverBound = "true";
            menu.addEventListener("pointerenter", cancelClose);
            menu.addEventListener("mouseenter", cancelClose);
            menu.addEventListener("pointerleave", scheduleClose);
            menu.addEventListener("mouseleave", scheduleClose);
          });
        };

        const bindTopNavigationHover = () => {
          document
            .querySelectorAll('[data-testid="stTopNavSection"]')
            .forEach((button) => {
              if (button.dataset.versevadHoverBound === "true") return;
              button.dataset.versevadHoverBound = "true";
              let hoverTimer = null;
              const openOnHover = () => {
                cancelClose();
                closeExpandedExcept(button);
                if (button.getAttribute("aria-expanded") === "true") {
                  bindMenuLeave();
                  return;
                }
                if (hoverTimer !== null) return;
                hoverTimer = window.setTimeout(() => {
                  hoverTimer = null;
                  closeExpandedExcept(button);
                  button.click();
                  window.requestAnimationFrame(bindMenuLeave);
                }, OPEN_DELAY_MS);
              };
              button.addEventListener("pointerenter", openOnHover);
              button.addEventListener("mouseenter", openOnHover);
              button.addEventListener("pointerover", openOnHover);
              button.addEventListener("pointerleave", () => {
                if (hoverTimer !== null) window.clearTimeout(hoverTimer);
                hoverTimer = null;
                scheduleClose();
              });
              button.addEventListener("mouseleave", () => {
                if (hoverTimer !== null) window.clearTimeout(hoverTimer);
                hoverTimer = null;
                scheduleClose();
              });
            });
          bindMenuLeave();
        };
        bindTopNavigationHover();
        window.requestAnimationFrame(bindTopNavigationHover);
        window.setTimeout(bindTopNavigationHover, 250);
        const observer = new MutationObserver(bindTopNavigationHover);
        observer.observe(document.body, { childList: true, subtree: true });
      })();
    </script>
    """


def render_top_navigation(*, include_local_routes: bool) -> WorkspaceRoute:
    """Render grouped top navigation and return the selected stable route."""

    grouped_pages: dict[str, list[st.Page]] = {}
    page_routes: dict[str, WorkspaceRoute] = {}
    workspace_pages: dict[str, st.Page] = {}
    for route in ROUTES:
        if route.local_only and not include_local_routes:
            continue
        page = st.Page(
            _empty_page,
            title=route.title,
            icon=route.icon,
            url_path=route.url_path,
            default=route.default,
        )
        grouped_pages.setdefault(route.section, []).append(page)
        page_routes[route.url_path] = route
        workspace_pages.setdefault(route.workspace_id, page)

    selected_page = st.navigation(grouped_pages, position="top")
    st.session_state["_versevad_workspace_pages"] = workspace_pages
    pending_workspace = st.session_state.pop("_pending_workspace_switch", None)
    if isinstance(pending_workspace, str):
        for route in ROUTES:
            if (
                route.workspace_id == pending_workspace
                and (include_local_routes or not route.local_only)
            ):
                target_page = next(
                    (
                        page
                        for page in grouped_pages.get(route.section, ())
                        if page.url_path == route.url_path
                    ),
                    None,
                )
                if target_page is not None:
                    st.switch_page(target_page)
                break
    selected_page.run()
    st.html(
        _top_navigation_hover_html(),
        width="content",
        unsafe_allow_javascript=True,
    )
    testing_override = st.session_state.get("_workspace_route_override")
    if isinstance(testing_override, str):
        for candidate in ROUTES:
            if (
                candidate.workspace_id == testing_override
                or candidate.url_path == testing_override
            ) and (include_local_routes or not candidate.local_only):
                return candidate
    selected_path = selected_page.url_path
    route = page_routes.get(selected_path)
    if route is not None:
        return route

    # Streamlit serves the default page at the root URL in some runtimes.
    return next(route for route in ROUTES if route.default)


def switch_to_workspace(workspace_id: str) -> None:
    """Navigate immediately to a registered workspace in the current session."""

    pages = st.session_state.get("_versevad_workspace_pages")
    if isinstance(pages, dict):
        page = pages.get(workspace_id)
        if page is not None:
            st.switch_page(page)
    st.session_state["_pending_workspace_switch"] = workspace_id
    st.rerun()


__all__ = [
    "ROUTES",
    "ROUTE_BY_PATH",
    "WORKSPACES",
    "WorkspaceRoute",
    "_top_navigation_hover_html",
    "render_top_navigation",
    "switch_to_workspace",
]
