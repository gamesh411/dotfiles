local theprimeagen_99 = {
  "ThePrimeagen/99",
  dependencies = {
    "saghen/blink.compat",
  },
  config = function()
    local _99 = require("99")

    local cwd = vim.uv.cwd()
    local basename = vim.fs.basename(cwd)
    _99.setup({
      provider = _99.Providers.KiroProvider,
      model = "claude-sonnet-4.6",
      logger = {
        level = _99.DEBUG,
        path = "/tmp/" .. basename .. ".99.debug",
        print_on_error = true,
      },
      -- When setting this to something that is not inside the CWD tools
      -- such as claude code or opencode will have permission issues
      -- and generation will fail refer to tool documentation to resolve
      -- https://opencode.ai/docs/permissions/#external-directories
      -- https://code.claude.com/docs/en/permissions#read-and-edit
      tmp_dir = "./tmp",

      --- Completions: #rules and @files in the prompt buffer
      completion = {
        -- I am going to disable these until i understand the
        -- problem better.  Inside of cursor rules there is also
        -- application rules, which means i need to apply these
        -- differently
        -- cursor_rules = "<custom path to cursor rules>"

        --- A list of folders where you have your own SKILL.md
        --- Expected format:
        --- /path/to/dir/<skill_name>/SKILL.md
        ---
        --- Example:
        --- Input Path:
        --- "scratch/custom_rules/"
        ---
        --- Output Rules:
        --- {path = "scratch/custom_rules/vim/SKILL.md", name = "vim"},
        --- ... the other rules in that dir ...
        ---
        custom_rules = {
          "scratch/custom_rules/",
        },

        --- Configure @file completion (all fields optional, sensible defaults)
        files = {
          -- enabled = true,
          -- max_file_size = 102400,     -- bytes, skip files larger than this
          -- max_files = 5000,            -- cap on total discovered files
          -- exclude = { ".env", ".env.*", "node_modules", ".git", ... },
        },

        --- What autocomplete do you use.  We currently only
        --- support cmp right now
        source = "blink",
      },

      --- WARNING: if you change cwd then this is likely broken
      --- ill likely fix this in a later change
      ---
      --- md_files is a list of files to look for and auto add based on the location
      --- of the originating request.  That means if you are at /foo/bar/baz.lua
      --- the system will automagically look for:
      --- /foo/bar/AGENT.md
      --- /foo/AGENT.md
      --- assuming that /foo is project root (based on cwd)
      md_files = {
        "AGENT.md",
      },
    })

    vim.keymap.set("v", "<leader>av", function()
      _99.visual({})
      vim.schedule(function() vim.cmd("startinsert") end)
    end, { desc = "99: visual edit selection" })

    vim.keymap.set("n", "<leader>ax", function()
      _99.stop_all_requests()
    end, { desc = "99: stop all requests" })

    vim.keymap.set("n", "<leader>as", function()
      _99.search({})
      vim.schedule(function() vim.cmd("startinsert") end)
    end, { desc = "99: search codebase" })

    vim.keymap.set("n", "<leader>ad", function()
      _99.vibe({})
      vim.schedule(function() vim.cmd("startinsert") end)
    end, { desc = "99: vibe" })

    vim.keymap.set("n", "<leader>ao", function()
      _99.open()
    end, { desc = "99: open" })

    vim.keymap.set("n", "<leader>aC", function()
      _99.clear_previous_requests()
    end, { desc = "99: clear previous requests" })

    vim.keymap.set("n", "<leader>at", function()
      _99.tutorial({})
      vim.schedule(function() vim.cmd("startinsert") end)
    end, { desc = "99: tutorial" })
  end,
}

return theprimeagen_99
