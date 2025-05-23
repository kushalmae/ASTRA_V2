function json_output = writeMetricToJson(times, values, scid, metric_name, threshold)
    % Convert metric data to JSON and write to file
    % Input:
    %   times - array of timestamps (datenum)
    %   values - array of metric values
    %   scid - spacecraft ID
    %   metric_name - name of the metric
    %   threshold - threshold value
    
    % Read config file
    [current_dir, ~, ~] = fileparts(mfilename('fullpath'));
    config_file = fullfile(current_dir, '..', '..', 'config', 'db_config.json');
    
    % Check if file exists
    if ~exist(config_file, 'file')
        error('Config file not found: %s', config_file);
    end
    
    fid = fopen(config_file, 'r');
    if fid == -1
        error('Could not open config file: %s', config_file);
    end
    
    raw = fread(fid, inf);
    str = char(raw');
    fclose(fid);
    config = jsondecode(str);
    
    % Get output directory from config
    output_dir = fullfile(current_dir, '..', '..', config.data_path);
    
    % Create structure array for JSON
    n_breaches = length(times);
    json_data = struct('scid', cell(n_breaches, 1), ...
                      'time', cell(n_breaches, 1), ...
                      'metric', cell(n_breaches, 1), ...
                      'value', cell(n_breaches, 1), ...
                      'threshold', cell(n_breaches, 1));
    
    % Fill the structure array
    for i = 1:n_breaches
        json_data(i).scid = scid;
        json_data(i).time = datestr(times(i), 'yyyy-mm-dd HH:MM:SS');  % Convert datenum to string
        json_data(i).metric = metric_name;
        json_data(i).value = values(i);
        json_data(i).threshold = threshold;
    end
    
    % Convert to JSON
    json_output = jsonencode(json_data);
    
    % Generate filename with metric name and timestamp
    filename = sprintf('%s_%s.json', metric_name, datestr(now, 'yyyymmdd_HHMMSS'));
    
    % Create full path
    full_path = fullfile(output_dir, filename);
    
    % Ensure output directory exists
    if ~exist(output_dir, 'dir')
        mkdir(output_dir);
    end
    
    % Write to file
    fid = fopen(full_path, 'w');
    if fid == -1
        error('Could not open output file: %s', full_path);
    end
    fprintf(fid, '%s', json_output);
    fclose(fid);
end