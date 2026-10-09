A = 23.196; T = 9.537; k = 0.95; Vhover = 2.5; Kp = 0.005;
mdl = 'kitticopter';
load_system(mdl);

scopes = find_system(mdl, 'BlockType', 'Scope');
for i = 1:numel(scopes)
    delete_block(scopes{i});
end
add_block('simulink/Sinks/To Workspace', [mdl '/ylog'], ...
    'VariableName', 'ylog', 'SaveFormat', 'Structure With Time');
add_line(mdl, 'Height/1', 'ylog/1', 'autorouting', 'on');

set_param(mdl, 'StopTime', '300');
out = sim(mdl);
y = out.ylog.signals.values;  t = out.ylog.time;
writematrix([t y], 'report/figures/simulink_step.csv');
fprintf('samples %d, final %.4f m, peak %.4f m, overshoot %.2f %%\n', ...
        numel(t), y(end), max(y), (max(y)-y(end))/y(end)*100);
close_system(mdl, 0);
