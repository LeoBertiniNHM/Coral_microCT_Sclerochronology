#  This software was developed by Leonardo Bertini (l.bertini@nhm.ac.uk) at the Natural History Museum (London,UK).
#
#  This is released as Supporting Material as part of the following publication:
#  "XXXXXX" (link to paper and DOI once published). #
#  #
#
#  Copyright (c) 2023
#
#  The code is distributed under the MIT license https://en.wikipedia.org/wiki/MIT_License

import cv2
import os
import matplotlib.pyplot as plt
from read_roi import read_roi_zip
from shapely.geometry import Polygon
from shapely.geometry import LineString
import numpy as np
import math
from hampel import hampel
import pandas as pd
import warnings
from pynverse import inversefunc
import time
import datetime

warnings.filterwarnings('ignore')

# defining paths OSX
rois_dir = "/Volumes/Seagate Hub/PhD/CORAL_SCIENCE_STASH/ROIS"
slabdir_raw = "/Volumes/Seagate Hub/PhD/CORAL_SCIENCE_STASH/Representative_Slabs_RAW_TIF"
slabdir_bh = "/Volumes/Seagate Hub/PhD/CORAL_SCIENCE_STASH/Representative_Slabs_BH_TIF"
excel_path = '/Users/leonardobertini/Desktop/Sclerochronology_Data.xlsx'  # this is where all calibration curve coefficients are saved
dir1 = '/Volumes/Seagate Hub/PhD/CORAL_RECONS_RAW'

# #Bristol ImagingLab Windows
# rois_dir = "D:\\PhD\\CORAL_SCIENCE_STASH\\ROIS"
# slabdir_raw = "D:\\PhD\\CORAL_SCIENCE_STASH\\Representative_Slabs_RAW_TIF"
# excel_path = "D:\\Users\\leonardobertini\\Desktop\\Sclerochronology_Data.xlsx"  # this is where all calibration curve coefficients are saved

# Windows CTlab Windows
# rois_dir = "G:\\PhD\\CORAL_SCIENCE_STASH\\ROIS"
# slabdir_raw = "G:\\PhD\\CORAL_SCIENCE_STASH\\Representative_Slabs_RAW_TIF"
# slabdir_bh =  "G:\\PhD\\CORAL_SCIENCE_STASH\\Representative_Slabs_BH_TIF"
# excel_path = "D:\\Users\\leonardobertini\\Desktop\\Sclerochronology_Data.xlsx" # this is where all calibration curve coefficients are saved
# dir1 = 'G:\\PhD\\CORAL_RECONS_RAW'


# COMPLETE todo find slab dirs to then match with roi files generated via ImageJ (Fiji)
slab_dirs = []
for root, dirs, files in os.walk(dir1):
    if 'Slabs' in os.path.abspath(root):
        print(os.path.abspath(root))
        slab_dirs.append(os.path.abspath(root))
slab_dirs.sort()

# COMPLETE TODO find all ROI zip files
roi_files = []
for each in os.listdir(rois_dir):
    if each.endswith('.zip'):
        roi_files.append(each)
roi_files.sort()

# # COMPLETE todo find matching tif slabs based on ROI name and copy to folder
# for roi in roi_files:
#     search_tag = roi.split('ROIS_')[1].split('.zip')[0].replace('_BH','')  # removing the 'BH' tag as we used BH and beautified images for coral dating
#     for dir in slab_dirs:
#         #print(dir)
#         TIF_population = os.listdir(dir)
#         for file in TIF_population:
#             if search_tag in file and not os.path.isfile(os.path.join(slabdir_raw, file)):  # skip files already copied (avoid cases so rotated slabs are not overwritten)
#                 print(search_tag)
#                 # print(file)
#                 # print(os.path.join(dir,file))
#                 copy_path = os.path.join(slabdir_raw, file)
#                 shutil.copyfile(os.path.join(dir, file), copy_path)  # copy the matching tif to slabdir_raw

# COMPLETE TODO find matching BH tif slabs based on ROI name
# dir2 = 'G:\\PhD\\CORAL_RECONS_BH'
# # COMPLETE todo find slab dirs to then match with roi files generated via ImageJ (Fiji)
# slab_dirs2 = []
# for root, dirs, files in os.walk(dir2):
#     if 'Slabs' in os.path.abspath(root):
#         print(os.path.abspath(root))
#         slab_dirs2.append(os.path.abspath(root))
# slab_dirs2.sort()
# #copying files to dedicated directory
# for roi in roi_files:
#     search_tag = roi.split('ROIS_')[1].split('.zip')[0]  # BH and beautified images for coral dating
#     for dir in slab_dirs2:
#         #print(dir)
#         TIF_population = os.listdir(dir)
#         for file in TIF_population:
#             if search_tag in file and not os.path.isfile(os.path.join(slabdir_bh, file)):  # skip files already copied (avoid cases so rotated slabs are not overwritten)
#                 print(search_tag)
#                 # print(file)
#                 # print(os.path.join(dir,file))
#                 copy_path = os.path.join(slabdir_bh, file)
#                 shutil.copyfile(os.path.join(dir, file), copy_path)  # copy the matching tif to slabdir_bh


##### Extracting measurements

# blank dictionary to be populated by measurements
slab_measurements = {'Slab_Name': [],
                     'Scan_Name': [],
                     'Slab Orientation': [],
                     'Voxel size_mm': [],
                     'AMR MeanDistance_cm': [],
                     'AMR MeanGrey': [],
                     'AMR MeanDensity_gcm3': [],
                     'Slab Area_cm2': [],
                     'Slab_vol_cm3': [],
                     'Slab Weight_g': [],
                     'MGA_TrackNames': [],
                     'MGA_TrackLengths_cm': [],
                     'MGA_TrackMeanGreys': [],
                     'MGA_TrackMeanDensities_gcm3': []}

roi_files = np.sort(roi_files).tolist()

# Complete todo loop over roi_files_filtered #only do for rois that have a respective raw slab
roi_files_filtered = []

for file in roi_files:
    for image_name in os.listdir(slabdir_raw):
        if image_name.split('.tif')[0] in file.split('ROIS_')[1].split('.zip')[0].replace('_BH', ''):
            roi_files_filtered.append(file)

time_start = time.time()
for file in roi_files_filtered:
    # find respective slab for roi file
    for image_name in os.listdir(slabdir_raw):
        if image_name.split('.tif')[0] in file.split('ROIS_')[1].split('.zip')[0].replace('_BH', ''):
            slabfile = image_name
            print(slabfile)  # found slab from which measurements will be extracted
            break

    slabraw = os.path.join(slabdir_raw, slabfile)  # COMPLETE TODO point to where complementary density slabs are saved

    # accessing information from ImageJ ROI zip file. It's a structured python dictionary
    fpath = os.path.join(rois_dir, file)
    roi = read_roi_zip(fpath)

    origin_key_name = []
    outline_key_name = []
    enclosed_area_key_name = []
    orientation = []

    for key in roi.keys():
        if 'Origin' in key:
            origin_key_name = key
        if 'Outline' in key:
            outline_key_name = key
        if 'Enclosed' in key:
            enclosed_area_key_name = key

    Origin = [roi[origin_key_name]['x'][0], roi[origin_key_name]['y'][0]]

    # calculating radial distance in vertical and horizontal slabs
    Outline = []
    seg_length = []
    if outline_key_name:
        orientation = 'Vertical'  # if there's an outline for AMR then this is a vertical slab
        Outline = list(zip(roi[outline_key_name]['x'], roi[outline_key_name]['y']))
        dist = []
        for point in Outline:
            dist.append(int(math.dist(Origin, point)))

        # Removing outlier distances (i.e., points close to origin
        dist_series = pd.Series(dist)  # List to Series
        outlier_indices = hampel(ts=dist_series, window_size=10)  # apply hampel moving median filter
        # Drop Outliers indices from Series
        filtered_distances = list(dist_series.drop(outlier_indices))
        AMR_MeanDistance = np.mean(filtered_distances)  # mean distance for AMR approach

    else:  # COMPLETE TODO calculate AMR planar distance from projected origin
        AMR_MeanDistance = []
        orientation = 'Horizontal'
        Outline = list(zip(roi[enclosed_area_key_name]['x'], roi[enclosed_area_key_name]['y']))
        dist = []
        for point in Outline:
            dist.append(int(math.dist(Origin, point)))

        # Removing outlier distances (i.e., points close to origin
        dist_series = pd.Series(dist)  # List to Series
        outlier_indices = hampel(ts=dist_series, window_size=10)  # apply hampel moving median filter
        # Drop Outliers indices from Series
        filtered_distances = list(dist_series.drop(outlier_indices))
        AMR_MeanDistance = np.mean(filtered_distances)  # mean distance for AMR approach

    # Getting Slab area
    x = roi[enclosed_area_key_name]['x']
    y = roi[enclosed_area_key_name]['y']
    pgon = Polygon(zip(x, y))  # x,y coordinates to form a closed polygon
    slab_area = pgon.area  # slab area for 'Totals approach' in pixels^2

    # COMPLETE TODO for each MGA_Transect, sample greys in a 2-corallite wide area around the line (fixed width of 2 mm)
    DataRaw = pd.read_excel(excel_path, sheet_name='AgeMeasurements', header=1)  # importing voxel size data

    # Get voxel size from spreadsheet
    found = False
    for name in DataRaw['Coral Colony']:
        slabfile_clean = slabfile.split('.aligned.am')[0]
        if name in slabfile_clean:
            found = True
            df_index = DataRaw.index[DataRaw['Coral Colony'] == name][0]
            vsize = pd.eval(DataRaw['VoxelSize mm'][df_index])
            print(f'Found voxel size for scan {name}: {vsize}')
            break
    if not found:
        print(f'The voxel size from scan {slabfile.split(".aligned.am")[0]} was not found')

    slab_area_mm2 = slab_area * vsize ** 2  # area in pixels x (voxel_size)^2
    slab_area_cm2 = slab_area_mm2 * 0.01

    # get slab depth and vol
    slab_depth_mm = int(file.split('Slab_num_')[1].split('_Slab_size')[0]) * vsize  # number of slices used x voxel_size
    slab_vol_mm3 = slab_area_mm2 * slab_depth_mm
    slab_vol_cm3 = slab_vol_mm3 * 0.001

    # Get calibration coefficients from spreadsheet
    Calibrations = pd.read_excel(excel_path, sheet_name='Densitometry_Calibrations')
    # find coefficients for specific scan
    found = False
    for name in Calibrations['Scan_name']:
        slabfile_clean = slabfile.split('.aligned.am')[0].replace('_BH', '')
        if name in slabfile_clean:
            found = True
            df_index = Calibrations.index[Calibrations['Scan_name'] == name][0]
            coeffs = pd.eval(Calibrations['Coefficients_High_Low_Order'][df_index])
            print(f'Found coefficients for scan {name}: {coeffs}')
            break
    if not found:
        print(f'The coefficients from scan {slabfile.split(".aligned.am")[0]} were not found')

    name = slabfile_clean  # this is the name to append to all saved images in the TO_CHECK folder
    img = []
    mask_slab = []

    # COMPLETE TODO get greys from masked area by polygon to get slab weight
    img = cv2.imread(slabraw, -1)  # read 16 bit image
    mask_slab = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
    xc = np.array(x)
    xc = np.r_[xc, xc[0]]
    yc = np.array(y)
    yc = np.r_[yc, yc[0]]

    contour = np.array([[[int(i[0]), int(i[1])]] for i in zip(xc, yc)])
    slab_masked = cv2.drawContours(mask_slab, [contour], 0, (255, 255, 255), -1)
    # save overlay of slab_mask in a TO_CHECK folder
    to_check_slab_mask = name + '_' + orientation + 'Slab_Mask.png'
    to_check_dir = os.path.join(os.path.dirname(rois_dir), 'TO_CHECK_PROBED_AREAS')

    if not os.path.exists(to_check_dir):
        os.makedirs(to_check_dir)

    # plt.imshow(img, cmap='gray')
    # plt.imshow(slab_masked, alpha=0.2)
    # plt.savefig(os.path.join(to_check_dir, to_check_slab_mask), dpi=300)
    # plt.clf()  #close window

    # Extract greys inside masked area of slab
    slab_greys = np.extract(mask_slab, img)

    # apply calibration curve to mean grey to retrieve densities and total slab weight
    a, b, c, d = coeffs
    func_p = (lambda x, a, b, c, d: a * (x ** 3) + b * (
            x ** 2) + c * x + d)  # define function to find inverse with the coefficients found
    # find inverse to get density estimate from gray value in domain of curve
    inverse_func = inversefunc(func_p, args=(a, b, c, d))

    weights = []
    # COMPLETE TODO get histogram of slab single binned from 0-2^16-1 with counts to improve speed
    t = time.time()
    slab_histo = np.histogram(slab_greys, bins=range(0, 65536))
    d = []
    for i in range(0, len(slab_histo[0])):
        count = slab_histo[0][i]
        grey = slab_histo[1][i]
        density = float(inverse_func(grey))
        # Apply weight test density correction
        density_estimate_corr = density * pd.eval(Calibrations['Density_Correction_Factor'][df_index])
        d.append(density_estimate_corr)
        mass = density_estimate_corr * (((
                                                 vsize ** 2) * slab_depth_mm) / 1000) * count  # voxelvolumes: *vsize (area in mm2 *0.01 for cm2), then multiply by slab depth for volume..
        weights.append(mass)
    print(f'Time elapsed is {time.time() - t} seconds')
    slab_mass = sum(weights)

    # defining probed area around transect line (2 mm is roughly the equivalent of 2 corallithes in width but can do sensitivity test)
    transectwidth_mm = 2
    transectwidth_px = transectwidth_mm / vsize  # width of box in pixels

    # find the corners of the box
    tracks = []
    for key in roi.keys():
        if 'Track' in key:
            tracks.append(key)

    tracks.sort()  # this sorts tracks

    # For each MGA_Track obtain length and mean grey
    MGA_transect_lengths = []
    MGA_transect_greys = []
    MGA_transect_densities = []

    if tracks:  # if this is a vertical slab where we have done a MGA_Track
        RECTANGLES_dic = {'RECTS': [],
                          'xpos': [],
                          'ypos': [],  # storing all rectangular masks in this variable for a single figure in the end
                          'TrackNames': []}
        for track_name in tracks:
            x1, y1, x2, y2 = roi[track_name]['x1'], roi[track_name]['y1'], roi[track_name]['x2'], roi[track_name][
                'y2']

            # define track line
            centre = LineString([(x1, y1), (x2, y2)])  # centre line
            track_length = math.dist((x1, y1), (x2, y2))  # MGA_ track_length in pixels

            print(f'The length in pixels for {track_name} is {track_length}')
            track_length_cm = track_length * vsize / 10

            width = transectwidth_px
            # define 2 lines running parallel to centre line
            left = centre.parallel_offset(width / 2,
                                          'left')  # line running parallel to centre of transect on one side
            right = centre.parallel_offset(width / 2,
                                           'right')  # #line running parallel to centre of transect on the other side. Note the different orientation for right offset

            # define top and bottom lines perpendicular to all 3 lines
            c = [left.xy[0][0], left.xy[1][0]]
            d = [right.xy[0][0], right.xy[1][0]]
            top = LineString([c, d])

            e = [left.xy[0][1], left.xy[1][1]]
            f = [right.xy[0][1], right.xy[1][1]]
            bottom = LineString([e, f])

            # visualise if lines are defined correctly and intersections make a closed rectangle that is tilted. Uncomment this block to see plot preview
            # imageplot = plt.imshow(img)
            # plot1 = plt.plot(*centre.xy)
            # plot2 = plt.plot(*left.xy)
            # plot3 = plt.plot(*right.xy)
            # plot4 = plt.plot(*top.xy)
            # plot5 = plt.plot(*bottom.xy)
            # plt.show()

            # mask array with same dim as slab image
            mask = []
            dummy_array = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
            # points given by intersections of lines (fully closed polygon passes through c, d, f, e in that order)
            pts = np.array([c, d, f, e], np.int32).reshape(-1, 1, 2)
            # mask with white inside the rectangle
            mask = cv2.fillConvexPoly(dummy_array, pts, 255)

            # save overlay of rectangles in a TO_CHECK folder
            to_check_img = name + '_' + track_name + '.png'
            to_check_dir = os.path.join(os.path.dirname(rois_dir), 'TO_CHECK_PROBED_AREAS')
            if not os.path.exists(to_check_dir):
                os.makedirs(to_check_dir)

            # save the overlap to check if all is correct
            plt.imshow(img, cmap='gray')
            plt.imshow(mask, alpha=0.1)
            # plt.show()
            plt.savefig(os.path.join(to_check_dir, to_check_img), dpi=300)
            plt.clf()  # close fig
            # apply the mask to extract greys
            greys = np.extract(mask, img)

            # Getting mean grey intensity within mask and apply calibration using poly3 fit extended phantom to obtain density
            # apply calibration curve to mean grey to retrieve density
            a, b, c, d = coeffs
            func_p = (lambda x, a, b, c, d: a * (x ** 3) + b * (
                    x ** 2) + c * x + d)  # define function to find inverse with the coefficients found
            # find inverse to get density estimate from gray value in domain of curve
            inverse_func = inversefunc(func_p, args=(a, b, c, d))
            # obtain density
            density_estimate = float(inverse_func(greys.mean()))
            # Apply weight test density correction
            density_estimate_corr = density_estimate * pd.eval(Calibrations['Density_Correction_Factor'][df_index])

            MGA_transect_greys.append(greys.mean())
            MGA_transect_densities.append(density_estimate_corr)
            MGA_transect_lengths.append(track_length_cm)

            RECTANGLES_dic['RECTS'].append(mask)
            RECTANGLES_dic['xpos'].append((x1 + x2) / 2)
            RECTANGLES_dic['ypos'].append((y1 + y2) / 2)
            RECTANGLES_dic['TrackNames'].append(track_name)

        # TODO save single figure with all tracks
        plt.imshow(img, cmap='gray')
        for idx in range(0, len(RECTANGLES_dic['TrackNames'])):
            rect = RECTANGLES_dic['RECTS'][idx]
            xtext = RECTANGLES_dic['xpos'][idx]
            ytext = RECTANGLES_dic['ypos'][idx]
            TrackName = RECTANGLES_dic['TrackNames'][idx]
            plt.imshow(rect, alpha=0.1)
            plt.text(xtext, ytext, TrackName, color="yellow", size=4)
        plt.axis('off')
        to_check_img_all_rect = name + '_AllTracks' + '.png'
        plt.savefig(os.path.join(to_check_dir, to_check_img_all_rect), bbox_inches='tight', transparent=False,
                    pad_inches=0, dpi=300)
        plt.clf()  # close fig
        # plt.show()

    else:
        MGA_transect_lengths.append('NA')
        MGA_transect_greys.append('NA')
        MGA_transect_densities.append('NA')

    # Complete TODO getting mean greys around AMR transects.
    OutlinesGreys = []
    OutlineDensities = []
    AMR_MeanGrey = []
    AMR_MeanDensity = []

    if Outline:  # get mean grey around outline
        for pairs in Outline:
            x1, y1, x2, y2 = Origin[0], Origin[1], pairs[0], pairs[1]

            # define track line
            centre = LineString([(x1, y1), (x2, y2)])  # centre line
            track_length = math.dist((x1, y1), (x2, y2))  # MGA_ track_length in pixels
            # print(f'The length in pixels for outline track {track_name} is {track_length}')

            width = transectwidth_px
            # define 2 lines running parallel to centre line
            left = centre.parallel_offset(width / 2,
                                          'left')  # line running parallel to centre of transect on one side
            right = centre.parallel_offset(width / 2,
                                           'right')  # #line running parallel to centre of transect on the other side. Note the different orientation for right offset

            # define top and bottom lines perpendicular to all 3 lines
            c = [left.xy[0][0], left.xy[1][0]]
            d = [right.xy[0][0], right.xy[1][0]]
            top = LineString([c, d])

            e = [left.xy[0][1], left.xy[1][1]]
            f = [right.xy[0][1], right.xy[1][1]]
            bottom = LineString([e, f])

            # mask array with same dim as slab image
            mask = []
            dummy_array = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
            # points given by intersections of lines (fully closed polygon passes through c, d, f, e in that order)
            pts = np.array([c, d, f, e], np.int32).reshape(-1, 1, 2)
            # mask with white inside the rectangle
            mask = cv2.fillConvexPoly(dummy_array, pts, 255)

            # apply the mask to extract greys
            greys = np.extract(mask, img)
            OutlinesGreys.append(greys.mean())

        # Getting mean grey intensity within mask and apply calibration using poly3 fit extended phantom to obtain density
        # apply calibration curve to mean grey to retrieve density
        a, b, c, d = coeffs
        func_p = (lambda x, a, b, c, d: a * (x ** 3) + b * (
                x ** 2) + c * x + d)  # define function to find inverse with the coefficients found
        # find inverse to get density estimate from gray value in domain of curve
        inverse_func = inversefunc(func_p, args=(a, b, c, d))
        # obtain density

        OverallGreyMean = np.mean(OutlinesGreys)
        density_estimate = float(inverse_func(OverallGreyMean))

        # Apply weight test density correction
        AMR_density_estimate_corr = density_estimate * pd.eval(Calibrations['Density_Correction_Factor'][df_index])

        AMR_MeanGrey.append(OverallGreyMean)
        AMR_MeanDensity.append(AMR_density_estimate_corr)
        if not isinstance(AMR_MeanDistance, str):
            AMR_MeanDistance = AMR_MeanDistance * vsize / 10  # distance in cm for AMR

    else:

        AMR_MeanGrey.append('NA')
        AMR_MeanDensity.append('NA')

    # updating dictionary after looping over all items
    slab_measurements['Slab_Name'].append(slabfile)
    slab_measurements['Scan_Name'].append(name)
    slab_measurements['Slab Orientation'].append(orientation)
    slab_measurements['Voxel size_mm'].append(vsize)
    slab_measurements['AMR MeanDistance_cm'].append(AMR_MeanDistance)
    slab_measurements['AMR MeanGrey'].append(AMR_MeanGrey)
    slab_measurements['AMR MeanDensity_gcm3'].append(AMR_MeanDensity)
    slab_measurements['Slab Area_cm2'].append(slab_area_cm2)
    slab_measurements['Slab Weight_g'].append(slab_mass)
    slab_measurements['Slab_vol_cm3'].append(slab_vol_cm3)
    slab_measurements['MGA_TrackNames'].append(tracks)
    slab_measurements['MGA_TrackLengths_cm'].append(MGA_transect_lengths)
    slab_measurements['MGA_TrackMeanGreys'].append(MGA_transect_greys)
    slab_measurements['MGA_TrackMeanDensities_gcm3'].append(MGA_transect_densities)

final_df = pd.DataFrame.from_dict(slab_measurements)

# Saving as excel
ROI_excel_complete_name = os.path.join(os.path.dirname(excel_path),
                                       'ROI_extraction_results-' + datetime.datetime.now().strftime(
                                           "%d%m%Y-%H%M%S") + '.xlsx')
final_df.to_excel(ROI_excel_complete_name)

time_end = time.time()

elapsed_time = time_end - time_start
print(f'Total execution in {elapsed_time / 60} min')
