local _99 = require("99")

local cwd = vim.uv.cwd()
local basename = vim.fs.basename(cwd)
_99.setup({
    provider = _99.Providers.KiroProvider,
    model = "auto",
    logger = {
        level = _99.DEBUG,
        path = "/tmp/" .. basename .. ".99.debug",
        print_on_error = true,
    },
    tmp_dir = "./tmp",
    completion = {
        custom_rules = { "scratch/custom_rules/" },
        files = {},
        source = "blink",
    },
    md_files = { "agents.md" },
})

require("which-key").add({
    { "<leader>a", group = "AI-99" },
    {
        -- Takes the current visual selection, opens a prompt buffer for instructions, then sends the selection + prompt to the AI provider which replaces the selection with the AI-generated result. Enters insert mode in the prompt buffer automatically.
        mode = "v",
        "<leader>av",
        function()
            _99.visual({})
            vim.schedule(function() vim.cmd("startinsert") end)
        end,
        desc = "99: visual edit selection",
    },
    {
        -- Stops/kills all in-flight AI requests. The underlying provider process is terminated and any partial results are discarded. Use this to cancel a request you no longer want.
        mode = "n",
        "<leader>ax",
        function() _99.stop_all_requests() end,
        desc = "99: stop all requests",
    },
    {
        -- Opens a prompt buffer for a codebase search query. Sends the prompt to the AI provider which searches across the project and returns a list of file locations with notes, populated into the quickfix list. Enters insert mode in the prompt buffer.
        mode = "n",
        "<leader>as",
        function()
            _99.search({})
            vim.schedule(function() vim.cmd("startinsert") end)
        end,
        desc = "99: search codebase",
    },
    {
        -- Opens a prompt buffer for a "vibe" session - an open-ended agentic coding session where the AI provider can freely make changes across the project (like a vibe-coding session). Enters insert mode in the prompt buffer.
        mode = "n",
        "<leader>ad",
        function()
            _99.vibe({})
            vim.schedule(function() vim.cmd("startinsert") end)
        end,
        desc = "99: vibe",
    },
    {
        -- Opens a selection window listing previous successful AI interactions. Selecting one re-opens its results: for search/vibe it opens the quickfix list, for tutorial it opens a split with the tutorial content. Also an action for the list of previous.
        mode = "n",
        "<leader>ao",
        function() _99.open() end,
        desc = "99: open",
    },
    {
        -- Clears the history of all previous search and visual operations. This removes them from the tracking list so they no longer appear in the open selector.
        mode = "n",
        "<leader>aC",
        function() _99.clear_previous_requests() end,
        desc = "99: clear previous requests",
    },
    {

        -- Opens a prompt buffer for a tutorial request. The AI generates an interactive tutorial/explanation which is then displayed in a vertical split with word wrap enabled. Enters insert mode in the prompt buffer.
        mode = "n",
        "<leader>at",
        function()
            _99.tutorial({})
            vim.schedule(function() vim.cmd("startinsert") end)
        end,
        desc = "99: tutorial",
    },
})
