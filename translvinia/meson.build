gnome = import('gnome')
python = import('python')
pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())

# Resources
blueprints = custom_target('blueprints',
  input: files(
    'shortcuts.blp',
    'window.blp',
    'widgets/lang_selector.blp',
    'widgets/lang_row.blp',
    'widgets/provider_preferences.blp',
    'widgets/speech_button.blp',
    'widgets/theme_switcher.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

gresource_conf = configuration_data()
gresource_conf.set('appstream-path', appstream_file.full_path())
gnome.compile_resources('translvinia',
  configure_file(
    input: 'translvinia.gresource.xml',
    output: 'translvinia.gresource.xml',
    configuration: gresource_conf,
  ),
  dependencies: [blueprints, appstream_file],
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

# Generate translvinia bin
configure_file(
  input: 'translvinia.in',
  output: 'translvinia',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

# Generate translvinia define module
configure_file(
  input: 'define.in',
  output: 'define.py',
  configuration: conf,
  install: true,
  install_dir: moduledir
)

launcher = join_paths(meson.project_build_root(), 'translvinia', meson.project_name())
run_target('run',
  command: [launcher]
)

subdir('search_provider')

# Python sources
sources = [
  '__init__.py',
  'asyncio.py',
  'history.py',
  'history_dialog.py',
  'languages.py',
  'main.py',
  'net.py',
  'preferences.py',
  'session.py',
  'settings.py',
  'shortcuts.py',
  'utils.py',
  'window.py',
]
# Install sources
install_data(sources, install_dir: moduledir)

# Install custom widgets
install_subdir('widgets', install_dir: moduledir)

# Install providers
install_subdir('providers', install_dir: moduledir)